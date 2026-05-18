<template>
  <div class="overview-page">
    <section class="panel-card overview-hero">
      <p class="eyebrow">Vaccination status</p>
      <h1 class="hero-title">Vaccination Status Overview</h1>
      <p class="section-note overview-subtitle">
        This dashboard summarizes quarterly COVID-19 vaccination rollout patterns across regions and income groups from
        2020 through the end of 2023. The views focus on rollout timing, coverage progress, and broad differences between
        group-level vaccination trajectories.
      </p>
    </section>

    <section class="panel-card overview-section">
      <AnimatedVaccinationRolloutChart />

      <article class="viz-card viz-card-wide">
        <div class="viz-toolbar">
          <div>
            <p class="viz-kicker">Overview 3</p>
            <h4>Cross-group Quarterly Vaccination Matrix</h4>
          </div>
          <div class="segment-control">
            <button
              v-for="option in groupMetricOptions"
              :key="option.key"
              type="button"
              class="segment-button"
              :class="{ active: selectedGroupMetric === option.key }"
              @click="selectedGroupMetric = option.key"
            >
              {{ option.label }}
            </button>
          </div>
        </div>
        <p class="viz-chart-intro">
          This matrix compares quarterly vaccination progress across world regions and income groups. Quarters run across
          the x-axis, groups run down the y-axis, and darker cells indicate higher values for the selected vaccination
          metric.
        </p>
        <p class="viz-chart-intro">
          The matrix highlights that vaccination expansion did not occur at the same pace everywhere. Higher-income and
          European groups generally show earlier and stronger coverage signals, while lower-income groups remain lighter
          for longer periods.
        </p>
        <p class="viz-chart-intro">
          The view should be read as a descriptive comparison of rollout timing rather than a complete explanation of
          country-level access, policy, or reporting differences.
        </p>
        <div v-if="groupMetricMatrix.groups.length" class="matrix-wrap">
          <div class="matrix-head" :style="heatmapGridStyle">
            <span></span>
            <span v-for="quarter in groupMetricMatrix.quarters" :key="quarter" class="matrix-quarter">{{ quarter }}</span>
          </div>
          <div
            v-for="group in groupMetricMatrix.groups"
            :key="group"
            class="matrix-row"
            :style="heatmapGridStyle"
          >
            <div class="matrix-label">{{ group }}</div>
            <div
              v-for="quarter in groupMetricMatrix.quarters"
              :key="`${group}-${quarter}`"
              class="matrix-cell"
              :style="{ background: groupCellColor(group, quarter) }"
              @mouseenter="showMatrixTooltip($event, group, quarter)"
              @mousemove="moveHoverTooltip($event)"
              @mouseleave="hideHoverTooltip"
            />
          </div>
        </div>
        <p v-else class="empty-state">No group-level quarterly data is available.</p>
      </article>

      <section class="panel-card overview-shell">
        <div class="overview-topbar">
          <div>
            <p class="viz-kicker">Global lens</p>
            <h2>Quarterly vaccination and case situation</h2>
            <p class="section-note overview-lens-note">
              These cards summarize the selected quarter by highlighting the strongest visible vaccination, case, and
              group-level signals. They provide a quick reference for the current frame before reading the detailed
              matrix and fitted rollout summary.
            </p>
          </div>
          <label class="control-stack slider-stack">
            <span>Quarter</span>
            <input
              v-model.number="selectedQuarterIndex"
              type="range"
              min="0"
              :max="Math.max(0, globalQuarters.length - 1)"
            />
          </label>
        </div>

        <div class="focus-chip quarter-chip">{{ selectedGlobalQuarter || "No quarter available" }}</div>

        <div class="overview-cards">
          <article class="overview-stat-card">
            <p class="viz-kicker">Vaccination leader</p>
            <h3>{{ vaccinationLeaderCard.title }}</h3>
            <p>{{ vaccinationLeaderCard.value }}</p>
          </article>
          <article class="overview-stat-card">
            <p class="viz-kicker">Case hotspot</p>
            <h3>{{ caseLeaderCard.title }}</h3>
            <p>{{ caseLeaderCard.value }}</p>
          </article>
          <article class="overview-stat-card">
            <p class="viz-kicker">{{ groupLeaderCard.kicker }}</p>
            <h3>{{ groupLeaderCard.title }}</h3>
            <p>{{ groupLeaderCard.value }}</p>
          </article>
          <article class="overview-stat-card">
            <p class="viz-kicker">Milestone pace</p>
            <h3>{{ milestoneLeaderCard.title }}</h3>
            <p>{{ milestoneLeaderCard.value }}</p>
          </article>
        </div>
      </section>

    </section>

    <CurveFitAnalysis />

    <p v-if="loadWarnings.length" class="data-warning">Data notes: {{ loadWarnings.join(" | ") }}</p>
    <div
      v-if="hoverTooltip"
      class="overview-tooltip"
      :style="{ left: `${hoverTooltip.x}px`, top: `${hoverTooltip.y}px` }"
    >
      <strong>{{ hoverTooltip.title }}</strong>
      <span v-for="line in hoverTooltip.lines" :key="line">{{ line }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { formatCompactNumber, loadCsvFromCandidates, pickField, toNumber, unique } from "../../utils/csv";
import AnimatedVaccinationRolloutChart from "../../components/AnimatedVaccinationRolloutChart.vue";
import CurveFitAnalysis from "../vaccination-rollout/CurveFitAnalysis.vue";

const MAX_QUARTER = "2023Q4";

const vaccinationMetricOptions = [
  {
    key: "vacc_rollout_speed_avg",
    label: "Rollout speed",
    description: "quarter-average smoothed first-dose flow per hundred people",
    formatter: (value) => `${Number(value).toFixed(3)} / 100`,
  },
  {
    key: "vacc_rolling_6m_per_hundred",
    label: "6-month dose intensity",
    description: "quarter-end rolling vaccinations over the last 6 months per hundred people",
    formatter: (value) => `${Number(value).toFixed(1)} / 100`,
  },
  {
    key: "vacc_rolling_12m_per_hundred",
    label: "12-month dose intensity",
    description: "quarter-end rolling vaccinations over the last 12 months per hundred people",
    formatter: (value) => `${Number(value).toFixed(1)} / 100`,
  },
];

const caseMetricOptions = [
  {
    key: "cases_new_cases_pm7_avg",
    label: "7-day avg new cases",
    description: "quarter-average 7-day smoothed new cases per million",
    formatter: (value) => `${Number(value).toFixed(0)} / 1M`,
  },
  {
    key: "cases_new_cases_pm_avg",
    label: "Daily new cases",
    description: "quarter-average daily new cases per million",
    formatter: (value) => `${Number(value).toFixed(0)} / 1M`,
  },
  {
    key: "cases_total_cases_pm_latest",
    label: "Cumulative burden",
    description: "quarter-end cumulative cases per million",
    formatter: (value) => `${formatCompactNumber(Number(value), 1)} / 1M`,
  },
];

const groupMetricOptions = [
  { key: "first_dose_progress", label: "First-dose progress", formatter: (value) => `${(Number(value) * 100).toFixed(1)}%` },
  { key: "full_vaccination_progress", label: "Full vaccination progress", formatter: (value) => `${(Number(value) * 100).toFixed(1)}%` },
];

const datasets = ref({
  countryQuarterly: [],
  groupQuarterlyLong: [],
  groupQuarterlyWide: [],
  groupMeta: [],
  groupMilestones: [],
  bubbleSeries: [],
});
const loadWarnings = ref([]);
const hoverTooltip = ref(null);
const selectedBubbleMonthIndex = ref(0);
let bubblePlaybackTimer = null;
const selectedVaccinationMetric = ref(vaccinationMetricOptions[2].key);
const selectedCaseMetric = ref(caseMetricOptions[0].key);
const selectedGroupMetric = ref("first_dose_progress");
const selectedQuarterIndex = ref(0);

const selectedVaccinationMetricMeta = computed(
  () => vaccinationMetricOptions.find((option) => option.key === selectedVaccinationMetric.value) || vaccinationMetricOptions[0]
);
const selectedCaseMetricMeta = computed(
  () => caseMetricOptions.find((option) => option.key === selectedCaseMetric.value) || caseMetricOptions[0]
);
const selectedGroupMetricMeta = computed(
  () => groupMetricOptions.find((option) => option.key === selectedGroupMetric.value) || groupMetricOptions[0]
);

onMounted(async () => {
  const [countryQuarterly, groupQuarterlyLong, groupQuarterlyWide, groupMeta, groupMilestones, bubbleSeries] = await Promise.all([
    loadCsvFromCandidates(["country_quarterly_overview.csv"]),
    loadCsvFromCandidates(["group_quarterly_long.csv"]),
    loadCsvFromCandidates(["group_quarterly_rollout_enriched.csv", "group_quarterly_rollout.csv"]),
    loadCsvFromCandidates(["group_meta.csv"]),
    loadCsvFromCandidates(["group_milestone_table.csv"]),
    loadCsvFromCandidates(["merged_cases_vaccination_4countries.csv"], "/analysis/cases-vaccination"),
  ]);

  datasets.value = {
    countryQuarterly: countryQuarterly.rows,
    groupQuarterlyLong: groupQuarterlyLong.rows,
    groupQuarterlyWide: groupQuarterlyWide.rows,
    groupMeta: groupMeta.rows,
    groupMilestones: groupMilestones.rows,
    bubbleSeries: bubbleSeries.rows,
  };

  loadWarnings.value = [countryQuarterly, groupQuarterlyLong, groupQuarterlyWide, groupMeta, groupMilestones, bubbleSeries]
    .map((item) => item.error)
    .filter(Boolean);

  selectedQuarterIndex.value = Math.max(0, globalQuarters.value.length - 1);
  selectedBubbleMonthIndex.value = Math.max(0, bubbleFrameMonths.value.length - 1);
});

onBeforeUnmount(() => {
  stopBubblePlayback();
});

const countryQuarterlyRows = computed(() =>
  datasets.value.countryQuarterly
    .map((row) => ({
      country: pickField(row, ["country", "location"]),
      quarter: pickField(row, ["quarter"]),
      vacc_rollout_speed_avg: toNumber(pickField(row, ["vacc_rollout_speed_avg"])),
      vacc_rolling_6m_per_hundred: toNumber(pickField(row, ["vacc_rolling_6m_per_hundred"])),
      vacc_rolling_12m_per_hundred: toNumber(pickField(row, ["vacc_rolling_12m_per_hundred"])),
      cases_new_cases_pm_avg: toNumber(pickField(row, ["cases_new_cases_pm_avg"])),
      cases_new_cases_pm7_avg: toNumber(pickField(row, ["cases_new_cases_pm7_avg"])),
      cases_total_cases_pm_latest: toNumber(pickField(row, ["cases_total_cases_pm_latest"])),
    }))
    .filter((row) => row.country && row.quarter && !isAggregateLocation(row.country))
);

const globalQuarters = computed(() =>
  unique(
    countryQuarterlyRows.value
      .filter(
        (row) =>
          Number.isFinite(row.vacc_rollout_speed_avg) ||
          Number.isFinite(row.vacc_rolling_6m_per_hundred) ||
          Number.isFinite(row.vacc_rolling_12m_per_hundred)
      )
      .map((row) => row.quarter)
  )
    .filter((quarter) => quarter && isQuarterOnOrBefore(quarter, MAX_QUARTER))
    .sort(sortQuarterKeys)
);

watch(
  () => globalQuarters.value.length,
  (length) => {
    if (!length) {
      selectedQuarterIndex.value = 0;
      return;
    }
    if (selectedQuarterIndex.value > length - 1) {
      selectedQuarterIndex.value = length - 1;
    }
  }
);

const selectedGlobalQuarter = computed(() => globalQuarters.value[selectedQuarterIndex.value] || "");

const bubbleSeriesRows = computed(() =>
  datasets.value.bubbleSeries
    .map((row) => {
      const date = pickField(row, ["date"]);
      const dateObject = new Date(date);
      if (Number.isNaN(dateObject.getTime())) {
        return null;
      }

      return {
        country: pickField(row, ["country", "location"]),
        monthKey: `${dateObject.getUTCFullYear()}-${String(dateObject.getUTCMonth() + 1).padStart(2, "0")}`,
        vaccinationRate: toNumber(pickField(row, ["vaccination_rate"])),
        caseRate: toNumber(pickField(row, ["new_cases_pm_7d", "new_cases_pm_7d_after_0d"])),
        casePressure: toNumber(pickField(row, ["new_cases_per_million", "new_cases_pm_7d"])),
      };
    })
    .filter(
      (row) =>
        row &&
        row.country &&
        row.monthKey &&
        Number.isFinite(row.vaccinationRate) &&
        Number.isFinite(row.caseRate) &&
        Number.isFinite(row.casePressure)
    )
);

const bubbleFrames = computed(() => {
  const monthMap = {};

  bubbleSeriesRows.value.forEach((row) => {
    const frameKey = row.monthKey;
    if (!monthMap[frameKey]) {
      monthMap[frameKey] = {};
    }
    monthMap[frameKey][row.country] = row;
  });

  return Object.keys(monthMap)
    .sort()
    .map((monthKey) => ({
      monthKey,
      points: Object.values(monthMap[monthKey]).sort((left, right) => left.country.localeCompare(right.country)),
    }));
});

const bubbleFrameMonths = computed(() => bubbleFrames.value.map((frame) => frame.monthKey));

watch(
  () => bubbleFrameMonths.value.length,
  (length) => {
    if (!length) {
      selectedBubbleMonthIndex.value = 0;
      return;
    }
    if (selectedBubbleMonthIndex.value > length - 1) {
      selectedBubbleMonthIndex.value = length - 1;
    }
  }
);

const selectedBubbleMonth = computed(() => bubbleFrameMonths.value[selectedBubbleMonthIndex.value] || "");
const selectedBubbleFrame = computed(() => {
  const frame = bubbleFrames.value[selectedBubbleMonthIndex.value];
  return (frame?.points || []).map((point) => ({
    ...point,
    color: bubbleColor(point.country),
  }));
});

const bubbleChartBounds = {
  left: 78,
  right: 820,
  top: 48,
  bottom: 412,
};

const bubbleYMax = computed(() => {
  const max = Math.max(...bubbleSeriesRows.value.map((row) => row.caseRate), 0);
  if (max <= 0) {
    return 10;
  }
  return Math.ceil(max / 50) * 50;
});

const bubblePressureMax = computed(() => Math.max(...bubbleSeriesRows.value.map((row) => row.casePressure), 0));

const bubbleXAxisTicks = computed(() => [0, 20, 40, 60, 80, 100].map((value) => ({ value, label: `${value}`, x: bubbleX(value) })));
const bubbleYAxisTicks = computed(() =>
  [0, 0.25, 0.5, 0.75, 1].map((ratio) => {
    const value = bubbleYMax.value * ratio;
    return {
      value,
      label: value >= 100 ? `${Math.round(value)}` : value.toFixed(value >= 10 ? 0 : 1),
      y: bubbleY(value),
    };
  })
);

const bubbleVisibleMonthTicks = computed(() => {
  if (bubbleFrameMonths.value.length <= 6) {
    return bubbleFrameMonths.value;
  }
  const step = Math.ceil(bubbleFrameMonths.value.length / 6);
  return bubbleFrameMonths.value.filter((_, index) => index % step === 0 || index === bubbleFrameMonths.value.length - 1);
});

const vaccinationRows = computed(() =>
  countryQuarterlyRows.value.filter(
    (row) => row.quarter === selectedGlobalQuarter.value && Number.isFinite(row[selectedVaccinationMetric.value])
  )
);

const caseRows = computed(() =>
  countryQuarterlyRows.value.filter(
    (row) => row.quarter === selectedGlobalQuarter.value && Number.isFinite(row[selectedCaseMetric.value])
  )
);

const vaccinationRankedRows = computed(() => rankedRows(vaccinationRows.value, selectedVaccinationMetric.value).slice(0, 16));
const caseRankedRows = computed(() => rankedRows(caseRows.value, selectedCaseMetric.value).slice(0, 16));

const groupMetaOrder = computed(() => {
  const orderMap = {};
  datasets.value.groupMeta.forEach((row) => {
    const name = pickField(row, ["country", "group", "name"]);
    const order = toNumber(pickField(row, ["display_order", "order"]), Number.MAX_SAFE_INTEGER);
    if (name) {
      orderMap[name] = order;
    }
  });
  return orderMap;
});

const normalizedGroupLongRows = computed(() => {
  if (datasets.value.groupQuarterlyLong.length) {
    return datasets.value.groupQuarterlyLong
      .map((row) => ({
        group: pickField(row, ["country", "group"]),
        quarter: pickField(row, ["quarter"]),
        metric: pickField(row, ["metric"]),
        value: toNumber(pickField(row, ["value"])),
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
      }))
    )
    .filter((row) => row.group && row.quarter && row.metric && Number.isFinite(row.value));
});

const groupMetricMatrix = computed(() => {
  const groups = unique(normalizedGroupLongRows.value.map((row) => row.group)).sort((left, right) => {
    const leftOrder = groupMetaOrder.value[left] ?? Number.MAX_SAFE_INTEGER;
    const rightOrder = groupMetaOrder.value[right] ?? Number.MAX_SAFE_INTEGER;
    if (leftOrder !== rightOrder) {
      return leftOrder - rightOrder;
    }
    return left.localeCompare(right);
  });

  const quarters = unique(normalizedGroupLongRows.value.map((row) => row.quarter))
    .filter((quarter) => quarter && isQuarterOnOrBefore(quarter, MAX_QUARTER))
    .sort(sortQuarterKeys);
  const metricRows = normalizedGroupLongRows.value.filter(
    (row) => row.metric === selectedGroupMetric.value && isQuarterOnOrBefore(row.quarter, MAX_QUARTER)
  );
  const valueMap = metricRows.reduce((map, row) => {
    map[`${row.group}__${row.quarter}`] = row.value;
    return map;
  }, {});

  return { groups, quarters, valueMap };
});

const heatmapGridStyle = computed(() => ({
  gridTemplateColumns: `180px repeat(${Math.max(groupMetricMatrix.value.quarters.length, 1)}, 74px)`,
}));

const vaccinationLeaderCard = computed(() => {
  const leader = vaccinationRankedRows.value[0];
  return {
    title: leader?.country || "No data",
    value: leader
      ? `${selectedVaccinationMetricMeta.value.label}: ${selectedVaccinationMetricMeta.value.formatter(leader.value)}`
      : "No data in selected quarter",
  };
});

const caseLeaderCard = computed(() => {
  const leader = caseRankedRows.value[0];
  return {
    title: leader?.country || "No data",
    value: leader
      ? `${selectedCaseMetricMeta.value.label}: ${selectedCaseMetricMeta.value.formatter(leader.value)}`
      : "No data in selected quarter",
  };
});

const groupLeaderCard = computed(() => {
  const rows = normalizedGroupLongRows.value.filter(
    (row) => row.metric === selectedGroupMetric.value && row.quarter === selectedGlobalQuarter.value
  );
  const leader = [...rows].sort((left, right) => right.value - left.value)[0];
  return {
    kicker: selectedGroupMetric.value === "full_vaccination_progress" ? "Completion leader" : "Coverage leader",
    title: leader?.group || "No data",
    value: leader ? `${selectedGroupMetricMeta.value.label}: ${selectedGroupMetricMeta.value.formatter(leader.value)}` : "No group row in selected quarter",
  };
});

const milestoneLeaderCard = computed(() => {
  const milestones = datasets.value.groupMilestones
    .map((row) => ({
      group: pickField(row, ["country", "group"]),
      metric: pickField(row, ["metric"]),
      threshold: toNumber(pickField(row, ["threshold"])),
      quarter: pickField(row, ["first_quarter_reached"]),
    }))
    .filter((row) => row.group && row.metric === "full_vaccination_progress" && row.threshold === 0.75 && row.quarter);

  const earliest = [...milestones].sort((left, right) => sortQuarterKeys(left.quarter, right.quarter))[0];
  return {
    title: earliest?.group || "No milestone",
    value: earliest ? `Earliest 75% completion milestone: ${earliest.quarter}` : "Milestone table unavailable",
  };
});

const vaccinationNarrative = computed(() => {
  const leader = vaccinationRankedRows.value[0];
  return leader
    ? `${leader.country} has the strongest visible vaccination signal in ${selectedGlobalQuarter.value}. Higher bars indicate faster or denser rollout activity in the selected metric.`
    : "No stable vaccination signal is available for the selected quarter.";
});

const caseNarrative = computed(() => {
  const leader = caseRankedRows.value[0];
  return leader
    ? `${leader.country} has the highest visible case burden in ${selectedGlobalQuarter.value}. This keeps the overview legible without dense daily lines.`
    : "No stable case signal is available for the selected quarter.";
});

const groupNarrative = computed(() => {
  const firstQuarter = groupMetricMatrix.value.quarters[0] || "N/A";
  const latestQuarter = groupMetricMatrix.value.quarters[groupMetricMatrix.value.quarters.length - 1] || "N/A";
  return `The matrix summarizes group-level vaccination differences from ${firstQuarter} to ${latestQuarter}. It shows a staggered rollout pattern rather than a single synchronized global progression.`;
});

const bubbleNarrative = computed(() => {
  if (!selectedBubbleFrame.value.length) {
    return "The animated country comparison is currently unavailable.";
  }
  const leader = [...selectedBubbleFrame.value].sort((left, right) => right.caseRate - left.caseRate)[0];
  return `${selectedBubbleMonth.value} shows how the same countries move as vaccination coverage rises. ${leader.country} has the strongest visible case burden in the selected month, while bubble size keeps the pressure contrast legible during playback.`;
});

function rankedRows(rows, field) {
  const validRows = rows.filter((row) => Number.isFinite(row[field]));
  const maxValue = Math.max(...validRows.map((row) => row[field]), 0);
  return [...validRows]
    .sort((left, right) => right[field] - left[field])
    .map((row) => ({
      ...row,
      value: row[field],
      width: maxValue > 0 ? (row[field] / maxValue) * 100 : 0,
    }));
}

function groupCellValue(group, quarter) {
  return groupMetricMatrix.value.valueMap[`${group}__${quarter}`];
}

function groupCellLabel(group, quarter) {
  const value = groupCellValue(group, quarter);
  if (!Number.isFinite(value)) {
    return "N/A";
  }
  return selectedGroupMetricMeta.value.formatter(value);
}

function groupCellTitle(group, quarter) {
  return `${group} | ${quarter} | ${selectedGroupMetricMeta.value.label}: ${groupCellLabel(group, quarter)}`;
}

function groupCellColor(group, quarter) {
  const value = groupCellValue(group, quarter);
  if (!Number.isFinite(value)) {
    return "rgba(242, 230, 211, 0.45)";
  }
  const allValues = Object.values(groupMetricMatrix.value.valueMap).filter(Number.isFinite);
  const maxValue = Math.max(...allValues, 0);
  const ratio = maxValue > 0 ? value / maxValue : 0;
  const lightness = 92 - ratio * 46;
  return `hsl(155 42% ${lightness}%)`;
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

function isQuarterOnOrBefore(quarter, maxQuarter) {
  const quarterValue = quarterOrdinal(quarter);
  const maxValue = quarterOrdinal(maxQuarter);
  return Number.isFinite(quarterValue) && Number.isFinite(maxValue) && quarterValue <= maxValue;
}

function isAggregateLocation(country) {
  const aggregates = new Set([
    "World",
    "Africa",
    "Asia",
    "Europe",
    "North America",
    "South America",
    "Oceania",
    "European Union (27)",
    "European Union",
    "High-income countries",
    "Upper-middle-income countries",
    "Lower-middle-income countries",
    "Low-income countries",
    "International",
  ]);
  return aggregates.has(country) || /income/i.test(country);
}

function bubbleX(value) {
  const ratio = Math.max(0, Math.min(1, value / 100));
  return bubbleChartBounds.left + ratio * (bubbleChartBounds.right - bubbleChartBounds.left);
}

function bubbleY(value) {
  const max = bubbleYMax.value || 1;
  const ratio = Math.max(0, Math.min(1, value / max));
  return bubbleChartBounds.bottom - ratio * (bubbleChartBounds.bottom - bubbleChartBounds.top);
}

function bubbleRadius(value) {
  const max = bubblePressureMax.value || 1;
  const ratio = Math.max(0, Math.min(1, value / max));
  return 12 + ratio * 26;
}

function bubbleColor(country) {
  const palette = {
    China: "#d08755",
    Germany: "#5a9d7e",
    "United States": "#b85c38",
    Japan: "#7aa6d8",
  };
  return palette[country] || "#6ea58a";
}

function startBubblePlayback() {
  if (bubblePlaybackTimer || bubbleFrameMonths.value.length <= 1) {
    return;
  }
  bubblePlaybackTimer = window.setInterval(() => {
    if (selectedBubbleMonthIndex.value >= bubbleFrameMonths.value.length - 1) {
      selectedBubbleMonthIndex.value = 0;
      return;
    }
    selectedBubbleMonthIndex.value += 1;
  }, 1200);
}

function stopBubblePlayback() {
  if (!bubblePlaybackTimer) {
    return;
  }
  window.clearInterval(bubblePlaybackTimer);
  bubblePlaybackTimer = null;
}

function showMatrixTooltip(event, group, quarter) {
  const label = groupCellLabel(group, quarter);
  hoverTooltip.value = {
    x: event.clientX + 16,
    y: event.clientY + 16,
    title: group,
    lines: [quarter, `${selectedGroupMetricMeta.value.label}: ${label}`],
  };
}

function showBubbleTooltip(event, point) {
  hoverTooltip.value = {
    x: event.clientX + 16,
    y: event.clientY + 16,
    title: point.country,
    lines: [
      selectedBubbleMonth.value,
      `Vaccinated: ${point.vaccinationRate.toFixed(1)}%`,
      `7-day cases: ${point.caseRate.toFixed(1)} / 1M`,
      `Pressure: ${point.casePressure.toFixed(1)} / 1M`,
    ],
  };
}

function moveHoverTooltip(event) {
  if (!hoverTooltip.value) {
    return;
  }
  hoverTooltip.value = {
    ...hoverTooltip.value,
    x: event.clientX + 16,
    y: event.clientY + 16,
  };
}

function hideHoverTooltip() {
  hoverTooltip.value = null;
}
</script>

<style scoped>
.overview-page,
.overview-shell,
.overview-section {
  display: grid;
  gap: 1rem;
  min-width: 0;
}

.overview-page > .panel-card,
.overview-page > .overview-shell,
.overview-page > .overview-section {
  animation: fade-up 0.45s ease both;
}

.overview-hero {
  display: grid;
  gap: 0.35rem;
}

.overview-subtitle {
  margin: 0.25rem 0 0;
  max-width: 1080px;
  line-height: 1.62;
}

.overview-topbar {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: flex-start;
}

.overview-topbar h2 {
  margin: 0.15rem 0 0;
  font-size: 1.48rem;
}

.slider-stack {
  min-width: 260px;
}

.quarter-chip {
  min-width: 128px;
  justify-content: center;
}

.overview-cards {
  display: grid;
  gap: 0.9rem;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  min-width: 0;
}

.overview-stat-card {
  padding: 1rem 1rem 0.95rem;
  border-radius: 10px;
  border: 1px solid rgba(31, 42, 31, 0.08);
  background: rgba(255, 255, 255, 0.58);
}

.overview-stat-card h3 {
  margin: 0.12rem 0 0.45rem;
  font-size: 1.12rem;
}

.overview-stat-card p:last-child {
  margin: 0;
  color: var(--muted);
  line-height: 1.55;
}

.viz-chart-intro {
  margin: 0 0 0.9rem;
  color: var(--muted);
  line-height: 1.58;
}

.bubble-shell {
  display: grid;
  gap: 0.9rem;
}

.bubble-chart-card {
  padding: 1rem 1rem 0.8rem;
  border-radius: 22px;
  background: linear-gradient(180deg, rgba(255, 252, 247, 0.92) 0%, rgba(249, 245, 237, 0.9) 100%);
  border: 1px solid rgba(31, 42, 31, 0.08);
}

.bubble-heading {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  margin-bottom: 0.5rem;
}

.bubble-heading h5 {
  margin: 0;
  font-size: 1.16rem;
}

.bubble-heading span {
  color: var(--muted);
  font-weight: 600;
}

.bubble-chart {
  width: 100%;
  height: auto;
  display: block;
}

.bubble-grid {
  stroke: rgba(31, 42, 31, 0.1);
  stroke-width: 1;
}

.bubble-grid-vertical {
  stroke-dasharray: 4 7;
}

.bubble-axis {
  stroke: rgba(31, 42, 31, 0.22);
  stroke-width: 1.2;
}

.bubble-tick {
  fill: var(--muted);
  font-size: 12px;
}

.bubble-axis-label {
  fill: #304238;
  font-size: 14px;
  font-weight: 600;
}

.bubble-point-group {
  cursor: pointer;
}

.bubble-point {
  fill: var(--bubble-color);
  fill-opacity: 0.78;
  stroke: rgba(255, 255, 255, 0.9);
  stroke-width: 2;
  transition:
    cx 0.72s cubic-bezier(0.22, 1, 0.36, 1),
    cy 0.72s cubic-bezier(0.22, 1, 0.36, 1),
    r 0.72s cubic-bezier(0.22, 1, 0.36, 1),
    transform 0.18s ease,
    fill-opacity 0.18s ease;
  animation: bubble-in 0.55s ease both;
}

.bubble-point-group:hover .bubble-point {
  fill-opacity: 0.95;
  transform: scale(1.04);
}

.bubble-label {
  fill: #304238;
  font-size: 13px;
  font-weight: 600;
  pointer-events: none;
}

.bubble-controls {
  display: grid;
  gap: 0.85rem;
  align-items: center;
  grid-template-columns: auto minmax(0, 1fr);
}

.bubble-actions {
  display: flex;
  gap: 0.55rem;
}

.ghost-button {
  min-width: 76px;
}

.bubble-slider-block {
  display: grid;
  gap: 0.5rem;
}

.bubble-slider-meta {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: center;
}

.bubble-slider-meta span {
  color: var(--muted);
  font-weight: 600;
}

.bubble-month-rail {
  display: flex;
  justify-content: space-between;
  gap: 0.5rem;
  color: var(--muted);
  font-size: 0.72rem;
}

.ranking-stack {
  display: grid;
  gap: 0.75rem;
}

.ranking-row {
  display: grid;
  grid-template-columns: 180px minmax(0, 1fr);
  gap: 0.8rem;
  align-items: center;
  transition: transform 0.18s ease, opacity 0.18s ease;
}

.ranking-row:hover {
  transform: translateX(3px);
}

.ranking-meta {
  display: grid;
  gap: 0.16rem;
}

.ranking-meta span {
  color: var(--muted);
  font-size: 0.82rem;
}

.ranking-bar-track {
  height: 16px;
  border-radius: 999px;
  background: rgba(31, 42, 31, 0.09);
  overflow: hidden;
}

.ranking-bar {
  height: 100%;
  border-radius: 999px;
  transition: width 0.45s cubic-bezier(0.22, 1, 0.36, 1), filter 0.2s ease;
}

.ranking-row:hover .ranking-bar {
  filter: saturate(1.08) brightness(0.98);
}

.ranking-bar-vaccination {
  background: linear-gradient(90deg, #6ea58a 0%, #1d6b57 100%);
}

.ranking-bar-case {
  background: linear-gradient(90deg, #efb07a 0%, #b85c38 100%);
}

.empty-state {
  margin: 0;
  padding: 0.95rem 1rem;
  border-radius: 14px;
  background: rgba(242, 230, 211, 0.48);
  color: var(--muted);
}

.data-warning {
  margin: 0;
  color: var(--muted);
  font-size: 0.92rem;
}

:deep(.viz-card) {
  min-width: 0;
  overflow: hidden;
  border-radius: 10px;
}

:deep(.panel-card) {
  border-radius: 12px;
}

:deep(.segment-button) {
  border-radius: 8px;
}

:deep(.focus-chip) {
  border-radius: 8px;
}

.matrix-wrap {
  max-width: 100%;
  overflow-x: auto;
  overflow-y: hidden;
  padding-bottom: 0.3rem;
  display: grid;
  gap: 0.42rem;
}

.matrix-head,
.matrix-row {
  display: grid;
  gap: 0.5rem;
  align-items: center;
  width: max-content;
}

.matrix-quarter {
  font-size: 0.76rem;
  color: var(--muted);
  text-align: center;
}

.matrix-label {
  width: 180px;
  min-width: 180px;
  padding-right: 0.5rem;
  color: var(--muted);
  font-size: 0.78rem;
  font-weight: 700;
  line-height: 1.3;
  background: transparent;
  position: static;
}

.matrix-cell {
  width: 74px;
  min-width: 74px;
  height: 54px;
  border-radius: 4px;
  border: 1px solid rgba(31, 42, 31, 0.08);
  cursor: pointer;
  transition:
    background-color 0.35s cubic-bezier(0.22, 1, 0.36, 1),
    transform 0.18s ease,
    box-shadow 0.18s ease;
  animation: cell-in 0.4s ease both;
}

.matrix-cell:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 18px rgba(31, 42, 31, 0.12);
}

.overview-tooltip {
  position: fixed;
  z-index: 40;
  display: grid;
  gap: 0.16rem;
  max-width: 240px;
  padding: 0.72rem 0.8rem;
  border-radius: 6px;
  background: rgba(26, 45, 38, 0.94);
  color: #f6f1e6;
  box-shadow: 0 18px 34px rgba(18, 30, 25, 0.22);
  pointer-events: none;
  transform: translate3d(0, 0, 0);
}

.overview-tooltip strong {
  font-size: 0.9rem;
}

.overview-tooltip span {
  font-size: 0.78rem;
  line-height: 1.4;
  color: rgba(246, 241, 230, 0.86);
}

@keyframes fade-up {
  from {
    opacity: 0;
    transform: translateY(8px);
  }

  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes cell-in {
  from {
    opacity: 0;
    transform: scale(0.96);
  }

  to {
    opacity: 1;
    transform: scale(1);
  }
}

@keyframes bubble-in {
  from {
    opacity: 0;
    transform: scale(0.84);
  }

  to {
    opacity: 1;
    transform: scale(1);
  }
}

@media (max-width: 1080px) {
  .overview-topbar {
    flex-direction: column;
  }

  .overview-cards {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .ranking-row {
    grid-template-columns: 1fr;
  }

  .bubble-controls {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 680px) {
  .overview-cards {
    grid-template-columns: 1fr;
  }

  .slider-stack {
    min-width: 0;
    width: 100%;
  }

  .bubble-heading,
  .bubble-slider-meta {
    flex-direction: column;
    align-items: flex-start;
  }

  .bubble-month-rail {
    display: none;
  }
}
</style>
