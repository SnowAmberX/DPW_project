<template>
  <section class="panel-card section-card group-analytics">
    <div class="section-heading">
      <div>
        <p class="viz-kicker">Section A extension</p>
        <h2>Quarterly group rollout dashboard</h2>
      </div>
      <div class="segment-control">
        <button
          v-for="lens in lensOptions"
          :key="lens.key"
          type="button"
          class="segment-button"
          :class="{ active: selectedGroupLens === lens.key }"
          @click="selectedGroupLens = lens.key"
        >
          {{ lens.label }}
        </button>
      </div>
    </div>

    <p class="section-note body-note">
      This extension switches from individual countries to quarterly group-level summaries so the page can make stronger
      statements about rollout timing, acceleration, and completion gaps across regions and income bands.
    </p>

    <article class="viz-card viz-card-wide">
      <div class="viz-toolbar">
        <div>
          <p class="viz-kicker">G1</p>
          <h4>Quarterly rollout heatmap</h4>
        </div>
        <div class="segment-control">
          <button
            v-for="option in heatmapMetricOptions"
            :key="option.key"
            type="button"
            class="segment-button"
            :class="{ active: selectedHeatmapMetric === option.key }"
            @click="selectedHeatmapMetric = option.key"
          >
            {{ option.label }}
          </button>
        </div>
      </div>
      <p class="viz-chart-intro">
        Source: <code>group_quarterly_long.csv</code> plus ordering from <code>group_meta.csv</code>. The x-axis is
        quarter, the y-axis is group, and cell color encodes the quarter-level value for the selected vaccination metric.
      </p>
      <CountryQuarterHeatmap
        v-if="groupHeatmap.quarters.length && groupHeatmap.countries.length"
        :countries="groupHeatmap.countries"
        :quarters="groupHeatmap.quarters"
        :cells="groupHeatmap.cells"
        :metric-label="groupHeatmap.metricLabel"
        :value-formatter="groupHeatmap.valueFormatter"
      />
      <p v-else class="empty-state">Group quarterly heatmap data could not be assembled from the available files.</p>
      <p class="section-note body-note">{{ heatmapInsight }}</p>
    </article>

    <article class="viz-card viz-card-wide">
      <div class="viz-toolbar">
        <div>
          <p class="viz-kicker">G2</p>
          <h4>Group growth curves and turning points</h4>
        </div>
        <div class="segment-control">
          <button
            v-for="option in curveMetricOptions"
            :key="option.key"
            type="button"
            class="segment-button"
            :class="{ active: selectedCurveMetric === option.key }"
            @click="selectedCurveMetric = option.key"
          >
            {{ option.label }}
          </button>
        </div>
      </div>
      <p class="viz-chart-intro">
        Source: <code>group_quarterly_rollout_enriched.csv</code>, <code>group_qoq_change.csv</code>, and
        <code>group_peak_change_summary.csv</code>. The colored line tracks quarter-end progress, while the large marker
        shows the quarter where quarter-over-quarter growth reached its peak. That peak is used here as an explainable
        approximation of the rapid-expansion turning point.
      </p>

      <div v-if="curveSeries.length" class="group-chart-shell">
        <div class="group-legend">
          <button
            v-for="series in curveSeries"
            :key="series.group"
            type="button"
            class="legend-toggle"
            :class="{ muted: activeCurveGroup && activeCurveGroup !== series.group, active: activeCurveGroup === series.group }"
            @mouseenter="activeCurveGroup = series.group"
            @mouseleave="activeCurveGroup = ''"
          >
            <span class="legend-swatch" :style="{ background: series.color }"></span>
            {{ series.group }}
          </button>
        </div>

        <div ref="curveWrap" class="group-chart-surface" @mouseleave="clearCurveTooltip">
          <svg class="group-chart-svg" viewBox="0 0 940 430" role="img" aria-label="Quarterly group growth curve chart">
            <g>
              <line
                v-for="tick in curveYTicks"
                :key="`cy-${tick.value}`"
                class="grid-line"
                :x1="curveBounds.left"
                :x2="curveBounds.right"
                :y1="tick.y"
                :y2="tick.y"
              />
            </g>

            <line
              class="axis-line"
              :x1="curveBounds.left"
              :x2="curveBounds.right"
              :y1="curveBounds.bottom"
              :y2="curveBounds.bottom"
            />
            <line
              class="axis-line"
              :x1="curveBounds.left"
              :x2="curveBounds.left"
              :y1="curveBounds.top"
              :y2="curveBounds.bottom"
            />

            <g>
              <text
                v-for="tick in curveYTicks"
                :key="`cyl-${tick.value}`"
                class="axis-label"
                :x="curveBounds.left - 12"
                :y="tick.y + 4"
                text-anchor="end"
              >
                {{ tick.label }}
              </text>
              <text
                v-for="quarter in visibleCurveQuarters"
                :key="`cxl-${quarter.key}`"
                class="axis-label"
                :x="quarter.x"
                :y="curveBounds.bottom + 24"
                text-anchor="middle"
              >
                {{ quarter.key }}
              </text>
            </g>

            <g>
              <path
                v-for="series in curveSeries"
                :key="`${series.group}-path`"
                class="group-line"
                :class="{ muted: activeCurveGroup && activeCurveGroup !== series.group, active: activeCurveGroup === series.group }"
                :d="buildLinePath(series.points)"
                :stroke="series.color"
              />

              <circle
                v-for="series in curveSeries"
                :key="`${series.group}-peak`"
                class="peak-marker"
                :class="{ muted: activeCurveGroup && activeCurveGroup !== series.group, active: activeCurveGroup === series.group }"
                :cx="series.peakPoint.x"
                :cy="series.peakPoint.y"
                :fill="series.color"
                r="7"
              />

              <circle
                v-for="hoverPoint in curveHoverTargets"
                :key="hoverPoint.key"
                class="hover-target"
                :cx="hoverPoint.x"
                :cy="hoverPoint.y"
                r="11"
                @mouseenter="showCurveTooltip($event, hoverPoint)"
                @mousemove="showCurveTooltip($event, hoverPoint)"
              />
            </g>

            <text
              class="axis-title"
              :x="(curveBounds.left + curveBounds.right) / 2"
              y="418"
              text-anchor="middle"
            >
              Quarter
            </text>
            <text
              class="axis-title"
              x="20"
              :y="(curveBounds.top + curveBounds.bottom) / 2"
              :transform="`rotate(-90 20 ${(curveBounds.top + curveBounds.bottom) / 2})`"
              text-anchor="middle"
            >
              {{ selectedCurveMetricMeta.axisLabel }}
            </text>
          </svg>

          <div v-if="curveTooltip" class="chart-tooltip" :style="{ left: `${curveTooltip.left}px`, top: `${curveTooltip.top}px` }">
            <strong>{{ curveTooltip.title }}</strong>
            <span v-for="(line, index) in curveTooltip.lines" :key="`${curveTooltip.title}-${index}`">{{ line }}</span>
          </div>
        </div>
      </div>
      <p v-else class="empty-state">No representative group series are available for the selected lens.</p>
      <p class="section-note body-note">{{ curveInsight }}</p>
    </article>

    <article class="viz-card viz-card-wide">
      <div class="viz-toolbar">
        <div>
          <p class="viz-kicker">G3</p>
          <h4>Milestone timeline comparison</h4>
        </div>
        <div class="segment-control">
          <button
            v-for="option in milestoneMetricOptions"
            :key="option.key"
            type="button"
            class="segment-button"
            :class="{ active: selectedMilestoneMetric === option.key }"
            @click="selectedMilestoneMetric = option.key"
          >
            {{ option.label }}
          </button>
        </div>
      </div>
      <p class="viz-chart-intro">
        Source: <code>group_milestone_table.csv</code> and <code>group_meta.csv</code>. Each row shows the earliest
        quarter when a group reached 25%, 50%, and 75% of the selected vaccination metric.
      </p>

      <div v-if="milestoneRows.length" ref="milestoneWrap" class="group-chart-surface milestone-surface" @mouseleave="clearMilestoneTooltip">
        <svg class="group-chart-svg milestone-svg" :viewBox="`0 0 940 ${milestoneHeight}`" role="img" aria-label="Milestone timeline chart">
          <g>
            <line
              v-for="quarter in milestoneVisibleQuarters"
              :key="`mgrid-${quarter.key}`"
              class="grid-line"
              :x1="quarter.x"
              :x2="quarter.x"
              :y1="milestoneBounds.top"
              :y2="milestoneHeight - milestoneBounds.bottom"
            />
          </g>

          <line
            class="axis-line"
            :x1="milestoneBounds.left"
            :x2="milestoneBounds.right"
            :y1="milestoneHeight - milestoneBounds.bottom"
            :y2="milestoneHeight - milestoneBounds.bottom"
          />

          <g v-for="row in milestoneRows" :key="row.group">
            <text
              class="axis-label category-label"
              :x="milestoneBounds.left - 12"
              :y="row.y + 5"
              text-anchor="end"
            >
              {{ row.group }}
            </text>
            <line
              class="milestone-track"
              :x1="milestoneBounds.left"
              :x2="milestoneBounds.right"
              :y1="row.y"
              :y2="row.y"
            />
            <line
              v-if="row.path.length > 1"
              class="milestone-link"
              :x1="row.path[0].x"
              :x2="row.path[row.path.length - 1].x"
              :y1="row.y"
              :y2="row.y"
            />
            <circle
              v-for="point in row.path"
              :key="`${row.group}-${point.threshold}`"
              class="milestone-node"
              :cx="point.x"
              :cy="row.y"
              :fill="thresholdColors[point.threshold]"
              r="7"
              @mouseenter="showMilestoneTooltip($event, row.group, point)"
              @mousemove="showMilestoneTooltip($event, row.group, point)"
            />
          </g>

          <g>
            <text
              v-for="quarter in milestoneVisibleQuarters"
              :key="`mxl-${quarter.key}`"
              class="axis-label"
              :x="quarter.x"
              :y="milestoneHeight - milestoneBounds.bottom + 24"
              text-anchor="middle"
            >
              {{ quarter.key }}
            </text>
          </g>
        </svg>

        <div v-if="milestoneTooltip" class="chart-tooltip" :style="{ left: `${milestoneTooltip.left}px`, top: `${milestoneTooltip.top}px` }">
          <strong>{{ milestoneTooltip.title }}</strong>
          <span v-for="(line, index) in milestoneTooltip.lines" :key="`${milestoneTooltip.title}-${index}`">{{ line }}</span>
        </div>
      </div>
      <p v-else class="empty-state">Milestone timing data is unavailable for the selected metric and lens.</p>

      <div class="threshold-legend">
        <span v-for="threshold in milestoneThresholds" :key="threshold" class="legend-toggle static">
          <span class="legend-swatch" :style="{ background: thresholdColors[threshold] }"></span>
          {{ Math.round(threshold * 100) }}%
        </span>
      </div>
      <p class="section-note body-note">{{ milestoneInsight }}</p>
    </article>

    <article class="viz-card viz-card-wide">
      <div class="viz-toolbar">
        <div>
          <p class="viz-kicker">G4</p>
          <h4>Peak quarter-over-quarter acceleration</h4>
        </div>
        <div class="segment-control">
          <button
            v-for="option in milestoneMetricOptions"
            :key="`acc-${option.key}`"
            type="button"
            class="segment-button"
            :class="{ active: selectedAccelerationMetric === option.key }"
            @click="selectedAccelerationMetric = option.key"
          >
            {{ option.label }}
          </button>
        </div>
      </div>
      <p class="viz-chart-intro">
        Source: <code>group_peak_change_summary.csv</code>. The bar length is the largest quarter-over-quarter gain
        observed for each group, and the tooltip reports the quarter when that acceleration peak occurred.
      </p>
      <GroupedBarChart
        v-if="accelerationBarData.categories.length"
        title="Peak quarter-over-quarter acceleration"
        :categories="accelerationBarData.categories"
        :series="accelerationBarData.series"
        x-axis-label="Peak quarter-over-quarter gain"
        y-axis-label="Group"
        :y-tick-formatter="formatAccelerationTick"
        :tooltip-formatter="formatAccelerationTooltip"
      />
      <p v-else class="empty-state">Peak acceleration summary data is unavailable for the selected metric and lens.</p>
      <p class="section-note body-note">{{ accelerationInsight }}</p>
    </article>

    <div class="findings-grid">
      <article v-for="(item, index) in groupFindings" :key="`group-finding-${index}`" class="finding-card">
        <p class="viz-kicker">Group finding {{ index + 1 }}</p>
        <p>{{ item }}</p>
      </article>
    </div>

    <p v-if="loadWarnings.length" class="data-warning">Data notes: {{ loadWarnings.join(" | ") }}</p>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import CountryQuarterHeatmap from "./CountryQuarterHeatmap.vue";
import GroupedBarChart from "./GroupedBarChart.vue";
import { clampNumber, formatPercent, loadCsvFromCandidates, pickField, toNumber, unique } from "../../utils/csv";

const heatmapMetricOptions = [
  { key: "rollout_speed", label: "Rollout speed", formatter: (value) => `${Number(value).toFixed(3)} / 100` },
  { key: "first_dose_progress", label: "First-dose progress", formatter: (value) => `${(Number(value) * 100).toFixed(1)}%` },
  { key: "full_vaccination_progress", label: "Full vaccination progress", formatter: (value) => `${(Number(value) * 100).toFixed(1)}%` },
];

const curveMetricOptions = [
  { key: "first_dose_progress", label: "First-dose progress", axisLabel: "First-dose progress (%)", formatter: (value) => `${(Number(value) * 100).toFixed(1)}%` },
  { key: "full_vaccination_progress", label: "Full vaccination progress", axisLabel: "Full vaccination progress (%)", formatter: (value) => `${(Number(value) * 100).toFixed(1)}%` },
];

const milestoneMetricOptions = [
  { key: "first_dose_progress", label: "First dose" },
  { key: "full_vaccination_progress", label: "Full vaccination" },
];

const lensOptions = [
  { key: "region", label: "Regions" },
  { key: "income", label: "Income groups" },
  { key: "all", label: "All groups" },
];

const thresholdColors = {
  0.25: "#d38a46",
  0.5: "#4f7d6b",
  0.75: "#1d6b57",
};

const milestoneThresholds = [0.25, 0.5, 0.75];
const palette = ["#1d6b57", "#b85c38", "#4f7d6b", "#c47b2f", "#506f97", "#875167", "#465c3f"];

const datasets = ref({
  groupQuarterlyLong: [],
  groupQuarterlyWide: [],
  groupMeta: [],
  groupSummary: [],
  groupMilestones: [],
  groupPeakChange: [],
  groupQoq: [],
});
const loadWarnings = ref([]);

const selectedHeatmapMetric = ref("rollout_speed");
const selectedCurveMetric = ref("first_dose_progress");
const selectedMilestoneMetric = ref("first_dose_progress");
const selectedAccelerationMetric = ref("first_dose_progress");
const selectedGroupLens = ref("region");
const activeCurveGroup = ref("");
const curveTooltip = ref(null);
const milestoneTooltip = ref(null);
const curveWrap = ref(null);
const milestoneWrap = ref(null);

const curveBounds = { left: 78, right: 900, top: 26, bottom: 340 };
const milestoneBounds = { left: 190, right: 900, top: 24, bottom: 52 };

onMounted(async () => {
  const [groupQuarterlyLong, groupQuarterlyWide, groupMeta, groupSummary, groupMilestones, groupPeakChange, groupQoq] =
    await Promise.all([
      loadCsvFromCandidates(["group_quarterly_long.csv"]),
      loadCsvFromCandidates(["group_quarterly_rollout_enriched.csv", "group_quarterly_rollout.csv"]),
      loadCsvFromCandidates(["group_meta.csv"]),
      loadCsvFromCandidates(["group_summary.csv"]),
      loadCsvFromCandidates(["group_milestone_table.csv"]),
      loadCsvFromCandidates(["group_peak_change_summary.csv"]),
      loadCsvFromCandidates(["group_qoq_change.csv"]),
    ]);

  datasets.value = {
    groupQuarterlyLong: groupQuarterlyLong.rows,
    groupQuarterlyWide: groupQuarterlyWide.rows,
    groupMeta: groupMeta.rows,
    groupSummary: groupSummary.rows,
    groupMilestones: groupMilestones.rows,
    groupPeakChange: groupPeakChange.rows,
    groupQoq: groupQoq.rows,
  };

  loadWarnings.value = [groupQuarterlyLong, groupQuarterlyWide, groupMeta, groupSummary, groupMilestones, groupPeakChange, groupQoq]
    .map((item) => item.error)
    .filter(Boolean);
});

const groupMetaMap = computed(() =>
  datasets.value.groupMeta.reduce((map, row) => {
    const name = pickField(row, ["country", "group", "name"]);
    if (!name) {
      return map;
    }
    map[name] = {
      groupType: pickField(row, ["group_type", "grouptype"]),
      displayOrder: toNumber(pickField(row, ["display_order", "order"]), Number.MAX_SAFE_INTEGER),
    };
    return map;
  }, {})
);

const normalizedLongRows = computed(() => {
  if (datasets.value.groupQuarterlyLong.length) {
    return datasets.value.groupQuarterlyLong
      .map((row) => ({
        group: pickField(row, ["country", "group"]),
        quarter: pickField(row, ["quarter"]),
        metric: pickField(row, ["metric"]),
        value: toNumber(pickField(row, ["value"])),
        groupType: pickField(row, ["group_type", "grouptype"]) || groupMetaMap.value[pickField(row, ["country", "group"])]?.groupType || "",
        displayOrder: toNumber(pickField(row, ["display_order", "order"]), groupMetaMap.value[pickField(row, ["country", "group"])]?.displayOrder ?? Number.MAX_SAFE_INTEGER),
      }))
      .filter((row) => row.group && row.quarter && row.metric && Number.isFinite(row.value));
  }

  return datasets.value.groupQuarterlyWide
    .flatMap((row) =>
      ["rollout_speed", "first_dose_progress", "full_vaccination_progress"].map((metric) => ({
        group: pickField(row, ["country", "group"]),
        quarter: pickField(row, ["quarter"]),
        metric,
        value: toNumber(pickField(row, [metric])),
        groupType: pickField(row, ["group_type", "grouptype"]) || groupMetaMap.value[pickField(row, ["country", "group"])]?.groupType || "",
        displayOrder: toNumber(pickField(row, ["display_order", "order"]), groupMetaMap.value[pickField(row, ["country", "group"])]?.displayOrder ?? Number.MAX_SAFE_INTEGER),
      }))
    )
    .filter((row) => row.group && row.quarter && row.metric && Number.isFinite(row.value));
});

const summaryRows = computed(() =>
  datasets.value.groupSummary
    .map((row) => ({
      group: pickField(row, ["country", "group"]),
      peakRolloutSpeed: toNumber(pickField(row, ["peak_rollout_speed"])),
      avgRolloutSpeed: toNumber(pickField(row, ["avg_rollout_speed"])),
      finalFirstDose: toNumber(pickField(row, ["final_first_dose_progress", "max_first_dose_progress"])),
      finalFull: toNumber(pickField(row, ["final_full_vaccination_progress", "max_full_vaccination_progress"])),
      peakRolloutQuarter: pickField(row, ["peak_rollout_quarter"]),
      groupType: pickField(row, ["group_type"]) || groupMetaMap.value[pickField(row, ["country", "group"])]?.groupType || "",
      displayOrder: toNumber(pickField(row, ["display_order"]), groupMetaMap.value[pickField(row, ["country", "group"])]?.displayOrder ?? Number.MAX_SAFE_INTEGER),
    }))
    .filter((row) => row.group)
);

const milestoneEntries = computed(() =>
  datasets.value.groupMilestones
    .map((row) => ({
      group: pickField(row, ["country", "group"]),
      metric: pickField(row, ["metric"]),
      threshold: toNumber(pickField(row, ["threshold"])),
      quarter: pickField(row, ["first_quarter_reached"]),
      groupType: groupMetaMap.value[pickField(row, ["country", "group"])]?.groupType || "",
      displayOrder: groupMetaMap.value[pickField(row, ["country", "group"])]?.displayOrder ?? Number.MAX_SAFE_INTEGER,
    }))
    .filter((row) => row.group && row.metric && Number.isFinite(row.threshold) && row.quarter)
);

const peakChangeEntries = computed(() =>
  datasets.value.groupPeakChange
    .map((row) => ({
      group: pickField(row, ["country", "group"]),
      metric: pickField(row, ["metric"]),
      peakQuarter: pickField(row, ["peak_change_quarter"]),
      peakChange: toNumber(pickField(row, ["peak_qoq_change"])),
      groupType: groupMetaMap.value[pickField(row, ["country", "group"])]?.groupType || "",
      displayOrder: groupMetaMap.value[pickField(row, ["country", "group"])]?.displayOrder ?? Number.MAX_SAFE_INTEGER,
    }))
    .filter((row) => row.group && row.metric && row.peakQuarter && Number.isFinite(row.peakChange))
);

const groupList = computed(() =>
  unique(normalizedLongRows.value.map((row) => row.group)).sort((left, right) => compareGroups(left, right, groupMetaMap.value))
);

const lensGroups = computed(() => {
  if (selectedGroupLens.value === "all") {
    return groupList.value;
  }
  return groupList.value.filter((group) => {
    const type = groupMetaMap.value[group]?.groupType || "";
    return selectedGroupLens.value === "region"
      ? type.startsWith("region") || type === "global"
      : type === "income";
  });
});

const allQuarters = computed(() => unique(normalizedLongRows.value.map((row) => row.quarter)).filter(Boolean).sort(sortQuarterKeys));

const groupHeatmap = computed(() => {
  const metricRows = normalizedLongRows.value.filter((row) => row.metric === selectedHeatmapMetric.value);
  const groups = groupList.value;
  const quarters = unique(metricRows.map((row) => row.quarter)).filter(Boolean).sort(sortQuarterKeys);
  const cells = metricRows.map((row) => ({ country: row.group, quarter: row.quarter, value: row.value }));
  const formatter = heatmapMetricOptions.find((option) => option.key === selectedHeatmapMetric.value)?.formatter ?? ((value) => String(value));

  return {
    countries: groups,
    quarters,
    cells,
    metricLabel:
      selectedHeatmapMetric.value === "rollout_speed"
        ? "Quarter-average rollout speed"
        : `${selectedHeatmapMetric.value === "first_dose_progress" ? "Quarter-end first-dose progress" : "Quarter-end full vaccination progress"}`,
    valueFormatter: formatter,
  };
});

const selectedCurveMetricMeta = computed(
  () => curveMetricOptions.find((option) => option.key === selectedCurveMetric.value) || curveMetricOptions[0]
);

const curveSeries = computed(() => {
  const metricRows = normalizedLongRows.value.filter(
    (row) => row.metric === selectedCurveMetric.value && lensGroups.value.includes(row.group)
  );
  const peakMap = peakChangeEntries.value
    .filter((row) => row.metric === selectedCurveMetric.value)
    .reduce((map, row) => {
      map[row.group] = row;
      return map;
    }, {});

  return lensGroups.value
    .map((group, index) => {
      const points = allQuarters.value
        .map((quarter) => {
          const match = metricRows.find((row) => row.group === group && row.quarter === quarter);
          if (!match) {
            return null;
          }
          return {
            group,
            quarter,
            value: match.value,
            x: curveX(quarter),
            y: curveY(match.value),
          };
        })
        .filter(Boolean);

      const peakEntry = peakMap[group];
      const peakPoint = points.find((point) => point.quarter === peakEntry?.peakQuarter) || points[Math.max(0, points.length - 1)];
      if (!points.length || !peakPoint) {
        return null;
      }

      return {
        group,
        color: palette[index % palette.length],
        points,
        peakPoint,
        peakChange: peakEntry?.peakChange ?? null,
      };
    })
    .filter(Boolean);
});

const curveHoverTargets = computed(() =>
  curveSeries.value.flatMap((series) =>
    series.points.map((point) => ({
      key: `${series.group}-${point.quarter}`,
      group: series.group,
      quarter: point.quarter,
      value: point.value,
      x: point.x,
      y: point.y,
      color: series.color,
      peakQuarter: series.peakPoint.quarter,
      peakChange: series.peakChange,
    }))
  )
);

const curveYTicks = computed(() =>
  [0, 0.25, 0.5, 0.75, 1].map((ratio) => ({
    value: ratio,
    label: `${Math.round(ratio * 100)}%`,
    y: curveY(ratio),
  }))
);

const visibleCurveQuarters = computed(() =>
  allQuarters.value.map((key, index) => ({ key, x: curveX(key), index })).filter((item, index) => index % 2 === 0 || index === allQuarters.value.length - 1)
);

const milestoneRows = computed(() => {
  const rows = lensGroups.value
    .map((group, index) => {
      const points = milestoneEntries.value
        .filter((entry) => entry.group === group && entry.metric === selectedMilestoneMetric.value && milestoneThresholds.includes(entry.threshold))
        .sort((left, right) => left.threshold - right.threshold)
        .map((entry) => ({
          threshold: entry.threshold,
          quarter: entry.quarter,
          x: milestoneX(entry.quarter),
        }));

      return points.length
        ? {
            group,
            y: milestoneBounds.top + 34 + index * 52,
            path: points,
          }
        : null;
    })
    .filter(Boolean);

  return rows;
});

const milestoneHeight = computed(() => milestoneBounds.top + milestoneBounds.bottom + Math.max(milestoneRows.value.length, 1) * 52 + 20);
const milestoneVisibleQuarters = computed(() =>
  allQuarters.value.map((key, index) => ({ key, x: milestoneX(key), index })).filter((item, index) => index % 2 === 0 || index === allQuarters.value.length - 1)
);

const accelerationBarData = computed(() => {
  const entries = peakChangeEntries.value
    .filter((entry) => entry.metric === selectedAccelerationMetric.value && lensGroups.value.includes(entry.group))
    .sort((left, right) => compareGroups(left.group, right.group, groupMetaMap.value));

  return {
    categories: entries.map((entry) => entry.group),
    series: [
      {
        key: "peak-change",
        label: "Peak QoQ gain",
        color: "#1d6b57",
        values: entries.map((entry) => entry.peakChange),
      },
    ],
  };
});

const heatmapInsight = computed(() => {
  const summary = [...summaryRows.value];
  if (!summary.length) {
    return "No group summary rows are available for a stable heatmap conclusion.";
  }

  if (selectedHeatmapMetric.value === "rollout_speed") {
    const leader = summary.filter((row) => Number.isFinite(row.peakRolloutSpeed)).sort((left, right) => right.peakRolloutSpeed - left.peakRolloutSpeed)[0];
    return leader
      ? `${leader.group} shows the strongest early rollout burst, peaking at ${leader.peakRolloutSpeed.toFixed(3)} per hundred in ${leader.peakRolloutQuarter}. The darker early cells for Europe, the EU, and high-income groups indicate earlier concentration of rollout speed than lower-income groups.`
      : "The heatmap indicates that rollout speed was concentrated in a short early window for several groups.";
  }

  const targetField = selectedHeatmapMetric.value === "first_dose_progress" ? "finalFirstDose" : "finalFull";
  const leader = summary.filter((row) => Number.isFinite(row[targetField])).sort((left, right) => right[targetField] - left[targetField])[0];
  return leader
    ? `${leader.group} reaches the strongest late-stage ${selectedHeatmapMetric.value === "first_dose_progress" ? "first-dose" : "full-vaccination"} completion signal. The matrix also shows that lower-income groups remain lighter for longer, which indicates a later and slower progression through the same coverage stages.`
    : "The heatmap suggests that completion timing differed materially across groups.";
});

const curveInsight = computed(() => {
  const entries = peakChangeEntries.value
    .filter((entry) => entry.metric === selectedCurveMetric.value && lensGroups.value.includes(entry.group))
    .sort((left, right) => sortQuarterKeys(left.peakQuarter, right.peakQuarter));

  const earliest = entries[0];
  const strongest = [...entries].sort((left, right) => right.peakChange - left.peakChange)[0];
  if (!earliest || !strongest) {
    return "No stable peak-change summary is available to locate the rapid-expansion phase.";
  }

  return `${earliest.group} enters its fastest visible growth phase first in ${earliest.peakQuarter}, while ${strongest.group} records the strongest quarter-over-quarter gain at ${strongest.peakChange.toFixed(3)}. In this chart, that peak-growth quarter is used as the turning-point proxy because it marks the transition into the steepest expansion stage.`;
});

const milestoneInsight = computed(() => {
  const entries = milestoneEntries.value
    .filter((entry) => entry.metric === selectedMilestoneMetric.value && entry.threshold === 0.5 && lensGroups.value.includes(entry.group))
    .sort((left, right) => sortQuarterKeys(left.quarter, right.quarter));

  const earliest = entries[0];
  const latest = entries[entries.length - 1];
  if (!earliest || !latest) {
    return "Milestone timing is unavailable for a robust threshold comparison.";
  }

  const lag = quarterDistance(earliest.quarter, latest.quarter);
  return `${earliest.group} reaches the 50% milestone first in ${earliest.quarter}, while ${latest.group} arrives last in ${latest.quarter}. The gap between them is roughly ${lag} quarter${lag === 1 ? "" : "s"}, which makes the timing difference much more explicit than a standard line chart.`;
});

const accelerationInsight = computed(() => {
  const entries = peakChangeEntries.value
    .filter((entry) => entry.metric === selectedAccelerationMetric.value && lensGroups.value.includes(entry.group))
    .sort((left, right) => right.peakChange - left.peakChange);

  const strongest = entries[0];
  const weakest = entries[entries.length - 1];
  if (!strongest || !weakest) {
    return "Peak acceleration summaries are unavailable.";
  }

  return `${strongest.group} posts the highest peak acceleration in ${strongest.peakQuarter}, while ${weakest.group} shows the weakest burst. This supports a quantitative comparison of growth intensity rather than relying on visual impression alone.`;
});

const groupFindings = computed(() => {
  const speedLeader = [...summaryRows.value].filter((row) => lensGroups.value.includes(row.group)).sort((left, right) => right.avgRolloutSpeed - left.avgRolloutSpeed)[0];
  const firstPeak = peakChangeEntries.value
    .filter((entry) => entry.metric === "first_dose_progress" && lensGroups.value.includes(entry.group))
    .sort((left, right) => sortQuarterKeys(left.peakQuarter, right.peakQuarter))[0];
  const fullPeak = peakChangeEntries.value
    .filter((entry) => entry.metric === "full_vaccination_progress" && lensGroups.value.includes(entry.group))
    .sort((left, right) => sortQuarterKeys(left.peakQuarter, right.peakQuarter))[0];
  const full50 = milestoneEntries.value
    .filter((entry) => entry.metric === "full_vaccination_progress" && entry.threshold === 0.5 && lensGroups.value.includes(entry.group))
    .sort((left, right) => sortQuarterKeys(left.quarter, right.quarter));

  return [
    speedLeader
      ? `${speedLeader.group} has the highest average rollout speed in the selected lens at ${speedLeader.avgRolloutSpeed.toFixed(3)} per hundred, indicating the most sustained quarterly rollout intensity.`
      : "Average rollout speed differs substantially across groups.",
    firstPeak && fullPeak
      ? `${firstPeak.group} reaches the rapid first-dose expansion phase by ${firstPeak.peakQuarter}, while the full-vaccination turning point appears later, with ${fullPeak.group} peaking in ${fullPeak.peakQuarter}. This shows that completion generally lagged initial uptake.`
      : "First-dose and full-vaccination growth do not peak at the same time.",
    full50.length >= 2
      ? `${full50[0].group} reaches 50% full vaccination first in ${full50[0].quarter}, whereas ${full50[full50.length - 1].group} is latest in ${full50[full50.length - 1].quarter}, making the completion gap visible in discrete quarterly steps.`
      : "Milestone timing differs clearly across groups.",
  ];
});

function compareGroups(left, right, metaMap) {
  const leftOrder = metaMap[left]?.displayOrder ?? Number.MAX_SAFE_INTEGER;
  const rightOrder = metaMap[right]?.displayOrder ?? Number.MAX_SAFE_INTEGER;
  if (leftOrder !== rightOrder) {
    return leftOrder - rightOrder;
  }
  return left.localeCompare(right);
}

function sortQuarterKeys(left, right) {
  const leftMatch = String(left || "").match(/^(\d{4})Q(\d)$/);
  const rightMatch = String(right || "").match(/^(\d{4})Q(\d)$/);
  if (!leftMatch || !rightMatch) {
    return String(left || "").localeCompare(String(right || ""));
  }
  const leftYear = Number(leftMatch[1]);
  const rightYear = Number(rightMatch[1]);
  if (leftYear !== rightYear) {
    return leftYear - rightYear;
  }
  return Number(leftMatch[2]) - Number(rightMatch[2]);
}

function quarterOrdinal(quarter) {
  const match = String(quarter || "").match(/^(\d{4})Q(\d)$/);
  if (!match) {
    return null;
  }
  return Number(match[1]) * 4 + Number(match[2]) - 1;
}

function quarterDistance(left, right) {
  const leftOrdinal = quarterOrdinal(left);
  const rightOrdinal = quarterOrdinal(right);
  if (!Number.isFinite(leftOrdinal) || !Number.isFinite(rightOrdinal)) {
    return 0;
  }
  return rightOrdinal - leftOrdinal;
}

function curveX(quarter) {
  const index = allQuarters.value.indexOf(quarter);
  if (index < 0 || allQuarters.value.length <= 1) {
    return curveBounds.left;
  }
  const ratio = index / (allQuarters.value.length - 1);
  return curveBounds.left + ratio * (curveBounds.right - curveBounds.left);
}

function curveY(value) {
  return curveBounds.top + (1 - value) * (curveBounds.bottom - curveBounds.top);
}

function buildLinePath(points) {
  return points.map((point, index) => `${index === 0 ? "M" : "L"} ${point.x} ${point.y}`).join(" ");
}

function milestoneX(quarter) {
  const index = allQuarters.value.indexOf(quarter);
  if (index < 0 || allQuarters.value.length <= 1) {
    return milestoneBounds.left;
  }
  const ratio = index / (allQuarters.value.length - 1);
  return milestoneBounds.left + ratio * (milestoneBounds.right - milestoneBounds.left);
}

function showCurveTooltip(event, point) {
  const bounds = curveWrap.value?.getBoundingClientRect();
  if (!bounds) {
    return;
  }

  activeCurveGroup.value = point.group;
  curveTooltip.value = {
    title: point.group,
    lines: [
      `Quarter: ${point.quarter}`,
      `${selectedCurveMetricMeta.value.label}: ${selectedCurveMetricMeta.value.formatter(point.value)}`,
      point.quarter === point.peakQuarter && Number.isFinite(point.peakChange)
        ? `Peak QoQ gain: ${point.peakChange.toFixed(3)}`
        : `Turning point proxy: ${point.peakQuarter}`,
    ],
    left: clampNumber(event.clientX - bounds.left + 14, 12, bounds.width - 220),
    top: clampNumber(event.clientY - bounds.top - 12, 12, bounds.height - 88),
  };
}

function clearCurveTooltip() {
  curveTooltip.value = null;
  activeCurveGroup.value = "";
}

function showMilestoneTooltip(event, group, point) {
  const bounds = milestoneWrap.value?.getBoundingClientRect();
  if (!bounds) {
    return;
  }

  milestoneTooltip.value = {
    title: group,
    lines: [
      `${selectedMilestoneMetric.value === "first_dose_progress" ? "First dose" : "Full vaccination"} milestone`,
      `Threshold: ${Math.round(point.threshold * 100)}%`,
      `Reached in: ${point.quarter}`,
    ],
    left: clampNumber(event.clientX - bounds.left + 14, 12, bounds.width - 220),
    top: clampNumber(event.clientY - bounds.top - 12, 12, bounds.height - 88),
  };
}

function clearMilestoneTooltip() {
  milestoneTooltip.value = null;
}

function formatAccelerationTick(value) {
  return `${Number(value).toFixed(2)}`;
}

function formatAccelerationTooltip(category, bar) {
  const match = peakChangeEntries.value.find(
    (entry) => entry.group === category && entry.metric === selectedAccelerationMetric.value && entry.peakChange === bar.value
  );
  return {
    title: category,
    lines: [
      `Peak QoQ gain: ${Number(bar.value).toFixed(3)}`,
      match?.peakQuarter ? `Peak quarter: ${match.peakQuarter}` : null,
    ].filter(Boolean),
  };
}
</script>

<style scoped>
.group-analytics {
  display: grid;
  gap: 1rem;
}

.group-chart-shell {
  display: grid;
  gap: 0.8rem;
}

.group-legend,
.threshold-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
}

.group-chart-surface {
  position: relative;
  overflow: hidden;
}

.group-chart-svg {
  width: 100%;
  height: auto;
  display: block;
}

.legend-toggle {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  border: 1px solid rgba(31, 42, 31, 0.12);
  background: rgba(255, 250, 242, 0.94);
  color: var(--ink);
  border-radius: 999px;
  padding: 0.42rem 0.78rem;
  cursor: pointer;
  font: inherit;
  transition: opacity 0.24s ease, transform 0.24s ease;
}

.legend-swatch {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  flex: none;
}

.grid-line {
  stroke: rgba(31, 42, 31, 0.12);
  stroke-width: 1;
}

.axis-line {
  stroke: rgba(31, 42, 31, 0.28);
  stroke-width: 1.25;
}

.axis-label {
  fill: var(--muted);
  font-size: 12px;
}

.axis-title {
  fill: var(--ink);
  font-size: 13px;
  font-weight: 600;
}

.chart-tooltip {
  position: absolute;
  z-index: 20;
  display: grid;
  gap: 0.16rem;
  min-width: 180px;
  padding: 0.72rem 0.8rem;
  border-radius: 10px;
  background: rgba(20, 34, 28, 0.96);
  color: #f5f0e5;
  pointer-events: none;
  box-shadow: 0 14px 30px rgba(20, 34, 28, 0.2);
}

.chart-tooltip strong {
  font-size: 0.88rem;
}

.chart-tooltip span {
  font-size: 0.78rem;
  line-height: 1.42;
  color: rgba(245, 240, 229, 0.9);
}

.finding-card {
  padding: 1rem 1rem 0.95rem;
  border-radius: 18px;
  background: rgba(242, 230, 211, 0.52);
  border: 1px solid rgba(31, 42, 31, 0.08);
}

.finding-card p:last-child {
  margin: 0.2rem 0 0;
  line-height: 1.58;
  color: var(--ink);
}

.milestone-svg {
  min-height: 420px;
}

.legend-toggle.static {
  cursor: default;
}

.legend-toggle.muted,
.group-line.muted,
.peak-marker.muted {
  opacity: 0.2;
}

.legend-toggle.active,
.group-line.active,
.peak-marker.active {
  opacity: 1;
}

.group-line {
  fill: none;
  stroke-width: 3.2;
  stroke-linejoin: round;
  stroke-linecap: round;
  transition: opacity 0.2s ease;
}

.peak-marker {
  stroke: rgba(255, 255, 255, 0.95);
  stroke-width: 2;
  transition: opacity 0.2s ease;
}

.hover-target {
  fill: transparent;
  cursor: pointer;
}

.milestone-surface {
  padding-top: 0.2rem;
}

.milestone-track {
  stroke: rgba(31, 42, 31, 0.1);
  stroke-width: 1;
}

.milestone-link {
  stroke: rgba(31, 42, 31, 0.26);
  stroke-width: 2;
}

.milestone-node {
  stroke: rgba(255, 255, 255, 0.95);
  stroke-width: 2;
  cursor: pointer;
}

.category-label {
  font-size: 12px;
}

@media (max-width: 960px) {
  .group-chart-svg {
    min-width: 900px;
  }

  .group-chart-surface {
    overflow-x: auto;
  }
}
</style>
