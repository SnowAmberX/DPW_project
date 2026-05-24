<template>
  <article class="viz-card viz-card-wide">
    <div class="viz-toolbar">
      <div>
        <p class="viz-kicker">Animated view</p>
        <h4>Vaccination Rollout Paths Across Groups</h4>
      </div>
      <div class="segment-control">
        <button
          v-for="option in metricOptions"
          :key="option.key"
          type="button"
          class="segment-button"
          :class="{ active: selectedMetric === option.key }"
          @click="selectedMetric = option.key"
        >
          {{ option.label }}
        </button>
      </div>
    </div>

    <p class="viz-chart-intro">
      This chart compares quarterly vaccination rollout trajectories across representative regions and income groups from
      2020 through the end of 2023. Each line tracks one group over time, while the moving highlight shows the currently
      selected quarter.
    </p>
    <p class="viz-chart-intro">
      Rollout speed was concentrated in earlier pandemic stages for several higher-coverage groups, while completion
      measures changed more gradually as countries moved from initial uptake toward full vaccination.
    </p>
    <p class="viz-chart-intro">
      The line patterns therefore suggest a heterogeneous global rollout process, with timing and intensity varying
      substantially across regions and income bands rather than following one uniform path.
    </p>

    <div v-if="chartQuarters.length" class="rollout-shell">
      <div class="rollout-legend">
        <span v-for="series in lineSeries" :key="series.group" class="legend-chip">
          <i :style="{ background: series.color }"></i>
          {{ series.group }}
        </span>
      </div>

      <div class="rollout-chart-card">
        <div class="rollout-heading">
          <h5>Quarterly rollout comparison</h5>
          <span>{{ selectedQuarter }}</span>
        </div>

        <svg class="rollout-chart" viewBox="0 0 980 520" role="img" aria-label="Animated vaccination rollout line chart">
          <g>
            <line
              v-for="tick in yTicks"
              :key="`grid-${tick.value}`"
              :x1="chartBounds.left"
              :x2="chartBounds.right"
              :y1="tick.y"
              :y2="tick.y"
              class="rollout-grid"
            />
          </g>

          <rect
            :x="currentQuarterBandX - 20"
            :y="chartBounds.top"
            width="40"
            :height="chartBounds.bottom - chartBounds.top"
            class="rollout-band"
          />

          <line
            :x1="chartBounds.left"
            :x2="chartBounds.right"
            :y1="chartBounds.bottom"
            :y2="chartBounds.bottom"
            class="rollout-axis"
          />
          <line
            :x1="chartBounds.left"
            :x2="chartBounds.left"
            :y1="chartBounds.top"
            :y2="chartBounds.bottom"
            class="rollout-axis"
          />
          <line
            :x1="currentQuarterBandX"
            :x2="currentQuarterBandX"
            :y1="chartBounds.top"
            :y2="chartBounds.bottom"
            class="rollout-scrub"
          />

          <g>
            <text
              v-for="tick in yTicks"
              :key="`yl-${tick.value}`"
              :x="chartBounds.left - 14"
              :y="tick.y + 5"
              text-anchor="end"
              class="rollout-tick"
            >
              {{ tick.label }}
            </text>
            <text
              v-for="quarter in visibleQuarterTicks"
              :key="`ql-${quarter.key}`"
              :x="quarter.x"
              :y="chartBounds.bottom + 30"
              text-anchor="middle"
              class="rollout-tick"
            >
              {{ quarter.key }}
            </text>
          </g>

          <text
            :x="(chartBounds.left + chartBounds.right) / 2"
            y="496"
            text-anchor="middle"
            class="rollout-axis-label"
          >
            Quarter
          </text>
          <text
            :x="28"
            :y="(chartBounds.top + chartBounds.bottom) / 2"
            transform="rotate(-90 28 250)"
            text-anchor="middle"
            class="rollout-axis-label"
          >
            {{ selectedMetricMeta.axisLabel }}
          </text>

          <g v-for="series in lineSeries" :key="series.group">
            <path
              :d="linePath(series.visiblePoints)"
              class="rollout-line"
              :style="{ '--series-color': series.color }"
            />
            <g
              v-for="point in series.visiblePoints"
              :key="`${series.group}-${point.quarter}`"
              @mouseenter="showTooltip($event, series.group, point)"
              @mousemove="moveTooltip($event)"
              @mouseleave="hideTooltip"
            >
              <circle
                :cx="point.x"
                :cy="point.y"
                :r="point.quarter === selectedQuarter ? 8 : 4.4"
                class="rollout-point"
                :class="{ active: point.quarter === selectedQuarter }"
                :style="{ '--series-color': series.color }"
              />
            </g>
          </g>
        </svg>
      </div>

      <div class="rollout-controls">
        <div class="rollout-actions">
          <button type="button" class="segment-button active rollout-ghost" @click="startPlayback">Play</button>
          <button type="button" class="segment-button rollout-ghost" @click="stopPlayback">Stop</button>
        </div>
        <div class="rollout-slider-block">
          <div class="rollout-slider-meta">
            <strong>Quarter</strong>
            <span>{{ selectedQuarter }}</span>
          </div>
          <input
            v-model.number="selectedQuarterIndex"
            type="range"
            min="0"
            :max="Math.max(0, chartQuarters.length - 1)"
          />
        </div>
      </div>
    </div>

    <p v-else class="empty-state">The group rollout animation is unavailable because the source table could not be loaded.</p>

    <div
      v-if="tooltip"
      class="rollout-tooltip"
      :style="{ left: `${tooltip.x}px`, top: `${tooltip.y}px` }"
    >
      <strong>{{ tooltip.title }}</strong>
      <span v-for="line in tooltip.lines" :key="line">{{ line }}</span>
    </div>
  </article>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { loadCsvFromCandidates, pickField, toNumber, unique } from "../../utils/csv";

const metricOptions = [
  {
    key: "rollout_speed",
    label: "Rollout speed",
    axisLabel: "Quarterly rollout speed (/100)",
    formatter: (value) => `${Number(value).toFixed(3)} / 100`,
  },
  {
    key: "first_dose_progress",
    label: "First-dose progress",
    axisLabel: "People with first dose (%)",
    formatter: (value) => `${(Number(value) * 100).toFixed(1)}%`,
  },
  {
    key: "full_vaccination_progress",
    label: "Full vaccination progress",
    axisLabel: "Fully vaccinated (%)",
    formatter: (value) => `${(Number(value) * 100).toFixed(1)}%`,
  },
];

const MAX_QUARTER = "2023Q4";

const datasets = ref({
  groupQuarterlyLong: [],
  groupQuarterlyWide: [],
  groupMeta: [],
});
const loadWarnings = ref([]);
const tooltip = ref(null);
const selectedMetric = ref(metricOptions[0].key);
const selectedQuarterIndex = ref(0);
let playbackTimer = null;

const chartBounds = {
  left: 92,
  right: 918,
  top: 44,
  bottom: 428,
};

const palette = {
  "European Union (27)": "#1d6b57",
  Europe: "#3f8f73",
  "High-income countries": "#4f76b4",
  "Upper-middle-income countries": "#d08755",
  "Lower-middle-income countries": "#a86dbe",
  "Low-income countries": "#c9554e",
  World: "#7b8b72",
};

onMounted(async () => {
  const [groupQuarterlyLong, groupQuarterlyWide, groupMeta] = await Promise.all([
    loadCsvFromCandidates(["group_quarterly_long.csv"]),
    loadCsvFromCandidates(["group_quarterly_rollout_enriched.csv", "group_quarterly_rollout.csv"]),
    loadCsvFromCandidates(["group_meta.csv"]),
  ]);

  datasets.value = {
    groupQuarterlyLong: groupQuarterlyLong.rows,
    groupQuarterlyWide: groupQuarterlyWide.rows,
    groupMeta: groupMeta.rows,
  };

  loadWarnings.value = [groupQuarterlyLong, groupQuarterlyWide, groupMeta].map((item) => item.error).filter(Boolean);
  selectedQuarterIndex.value = Math.max(0, chartQuarters.value.length - 1);
});

onBeforeUnmount(() => {
  stopPlayback();
});

const selectedMetricMeta = computed(() => metricOptions.find((item) => item.key === selectedMetric.value) || metricOptions[0]);

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

const normalizedRows = computed(() => {
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

const preferredGroups = [
  "European Union (27)",
  "High-income countries",
  "Upper-middle-income countries",
  "Lower-middle-income countries",
  "Low-income countries",
  "World",
];

const availableGroups = computed(() =>
  unique(normalizedRows.value.map((row) => row.group)).sort((left, right) => {
    const leftOrder = groupMetaOrder.value[left] ?? Number.MAX_SAFE_INTEGER;
    const rightOrder = groupMetaOrder.value[right] ?? Number.MAX_SAFE_INTEGER;
    if (leftOrder !== rightOrder) {
      return leftOrder - rightOrder;
    }
    return left.localeCompare(right);
  })
);

const focusGroups = computed(() => {
  const matched = preferredGroups.filter((group) => availableGroups.value.includes(group));
  return matched.length ? matched : availableGroups.value.slice(0, 6);
});

const chartQuarters = computed(() =>
  unique(normalizedRows.value.map((row) => row.quarter))
    .filter((quarter) => quarter && isQuarterOnOrBefore(quarter, MAX_QUARTER))
    .sort(sortQuarterKeys)
);

watch(
  () => chartQuarters.value.length,
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

const selectedQuarter = computed(() => chartQuarters.value[selectedQuarterIndex.value] || "");

const metricRows = computed(() =>
  normalizedRows.value.filter(
    (row) => row.metric === selectedMetric.value && isQuarterOnOrBefore(row.quarter, MAX_QUARTER)
  )
);

const valueMap = computed(() =>
  metricRows.value.reduce((map, row) => {
    map[`${row.group}__${row.quarter}`] = row.value;
    return map;
  }, {})
);

const yMax = computed(() => {
  const values = metricRows.value.map((row) => row.value).filter(Number.isFinite);
  const maxValue = Math.max(...values, 0);
  if (selectedMetric.value === "rollout_speed") {
    return maxValue > 0 ? Math.ceil(maxValue / 0.05) * 0.05 : 0.1;
  }
  return Math.max(1, Math.ceil(maxValue * 10) / 10);
});

const yTicks = computed(() =>
  [0, 0.25, 0.5, 0.75, 1].map((ratio) => {
    const value = yMax.value * ratio;
    return {
      value,
      label: selectedMetric.value === "rollout_speed" ? value.toFixed(2) : `${Math.round(value * 100)}%`,
      y: chartY(value),
    };
  })
);

const lineSeries = computed(() =>
  focusGroups.value.map((group, seriesIndex) => {
    const points = chartQuarters.value
      .map((quarter, quarterIndex) => {
        const value = valueMap.value[`${group}__${quarter}`];
        if (!Number.isFinite(value)) {
          return null;
        }
        return {
          group,
          quarter,
          quarterIndex,
          value,
          x: chartX(quarterIndex),
          y: chartY(value),
        };
      })
      .filter(Boolean);

    return {
      group,
      color: palette[group] || fallbackColor(seriesIndex),
      points,
      visiblePoints: points.filter((point) => point.quarterIndex <= selectedQuarterIndex.value),
    };
  })
);

const currentQuarterBandX = computed(() => chartX(selectedQuarterIndex.value));

const visibleQuarterTicks = computed(() => {
  if (chartQuarters.value.length <= 8) {
    return chartQuarters.value.map((key, index) => ({ key, x: chartX(index) }));
  }
  return chartQuarters.value
    .map((key, index) => ({ key, index, x: chartX(index) }))
    .filter((item, index) => index % 2 === 0 || index === chartQuarters.value.length - 1);
});

const narrative = computed(() => {
  const currentRows = lineSeries.value
    .map((series) => {
      const point = series.points.find((item) => item.quarter === selectedQuarter.value);
      return point ? { group: series.group, value: point.value } : null;
    })
    .filter(Boolean);

  if (!currentRows.length) {
    return "No stable rollout path is available for the selected metric.";
  }

  const leader = [...currentRows].sort((left, right) => right.value - left.value)[0];
  return `${selectedQuarter.value} highlights how representative regions and income groups diverge on ${selectedMetricMeta.value.label.toLowerCase()}. ${leader.group} is highest in the current frame, but the chart should be read as a broad timing comparison rather than a complete explanation of rollout conditions.`;
});

function chartX(index) {
  if (chartQuarters.value.length <= 1) {
    return (chartBounds.left + chartBounds.right) / 2;
  }
  const ratio = index / (chartQuarters.value.length - 1);
  return chartBounds.left + ratio * (chartBounds.right - chartBounds.left);
}

function chartY(value) {
  const max = yMax.value || 1;
  const ratio = Math.max(0, Math.min(1, value / max));
  return chartBounds.bottom - ratio * (chartBounds.bottom - chartBounds.top);
}

function linePath(points) {
  if (!points.length) {
    return "";
  }
  return points.map((point, index) => `${index === 0 ? "M" : "L"} ${point.x} ${point.y}`).join(" ");
}

function startPlayback() {
  if (playbackTimer || chartQuarters.value.length <= 1) {
    return;
  }
  playbackTimer = window.setInterval(() => {
    if (selectedQuarterIndex.value >= chartQuarters.value.length - 1) {
      selectedQuarterIndex.value = 0;
      return;
    }
    selectedQuarterIndex.value += 1;
  }, 1100);
}

function stopPlayback() {
  if (!playbackTimer) {
    return;
  }
  window.clearInterval(playbackTimer);
  playbackTimer = null;
}

function showTooltip(event, group, point) {
  tooltip.value = {
    x: event.clientX + 16,
    y: event.clientY + 16,
    title: group,
    lines: [point.quarter, `${selectedMetricMeta.value.label}: ${selectedMetricMeta.value.formatter(point.value)}`],
  };
}

function moveTooltip(event) {
  if (!tooltip.value) {
    return;
  }
  tooltip.value = {
    ...tooltip.value,
    x: event.clientX + 16,
    y: event.clientY + 16,
  };
}

function hideTooltip() {
  tooltip.value = null;
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

function fallbackColor(index) {
  const colors = ["#1d6b57", "#4f76b4", "#d08755", "#a86dbe", "#c9554e", "#7b8b72"];
  return colors[index % colors.length];
}
</script>

<style scoped>
.rollout-shell {
  display: grid;
  gap: 0.9rem;
}

.rollout-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
}

.legend-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.45rem 0.75rem;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid rgba(31, 42, 31, 0.09);
  color: #304238;
  font-size: 0.84rem;
  font-weight: 600;
}

.legend-chip i {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  display: block;
}

.rollout-chart-card {
  padding: 1rem 1rem 0.85rem;
  border-radius: 10px;
  background: linear-gradient(180deg, rgba(255, 252, 247, 0.92) 0%, rgba(249, 245, 237, 0.9) 100%);
  border: 1px solid rgba(31, 42, 31, 0.08);
}

.rollout-heading {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: center;
  margin-bottom: 0.45rem;
}

.rollout-heading h5 {
  margin: 0;
  font-size: 1.16rem;
}

.rollout-heading span {
  color: var(--muted);
  font-weight: 600;
}

.rollout-chart {
  width: 100%;
  height: auto;
  display: block;
}

.rollout-grid {
  stroke: rgba(31, 42, 31, 0.09);
  stroke-width: 1;
}

.rollout-band {
  fill: rgba(111, 163, 138, 0.12);
  transition: x 0.75s cubic-bezier(0.22, 1, 0.36, 1);
}

.rollout-axis,
.rollout-scrub {
  stroke: rgba(31, 42, 31, 0.24);
  stroke-width: 1.15;
}

.rollout-scrub {
  stroke-dasharray: 5 8;
  transition: x1 0.75s cubic-bezier(0.22, 1, 0.36, 1), x2 0.75s cubic-bezier(0.22, 1, 0.36, 1);
}

.rollout-tick {
  fill: var(--muted);
  font-size: 12px;
}

.rollout-axis-label {
  fill: #304238;
  font-size: 14px;
  font-weight: 600;
}

.rollout-line {
  fill: none;
  stroke: var(--series-color);
  stroke-width: 3.2;
  stroke-linecap: round;
  stroke-linejoin: round;
  opacity: 0.95;
  transition: d 0.75s cubic-bezier(0.22, 1, 0.36, 1);
}

.rollout-point {
  fill: var(--series-color);
  stroke: rgba(255, 255, 255, 0.92);
  stroke-width: 2;
  opacity: 0.85;
  transition:
    cx 0.75s cubic-bezier(0.22, 1, 0.36, 1),
    cy 0.75s cubic-bezier(0.22, 1, 0.36, 1),
    r 0.22s ease,
    opacity 0.22s ease,
    filter 0.22s ease;
}

.rollout-point.active {
  opacity: 1;
  filter: drop-shadow(0 6px 10px rgba(31, 42, 31, 0.18));
}

.rollout-controls {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 0.85rem;
  align-items: center;
}

.rollout-actions {
  display: flex;
  gap: 0.55rem;
}

.rollout-ghost {
  min-width: 76px;
}

.rollout-slider-block {
  display: grid;
  gap: 0.5rem;
}

.rollout-slider-meta {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: center;
}

.rollout-slider-meta span {
  color: var(--muted);
  font-weight: 600;
}

.warning-note {
  margin-top: 0.3rem;
  color: var(--muted);
  font-size: 0.88rem;
}

.viz-chart-intro {
  color: rgba(94, 107, 96, 0.9);
}

.rollout-tooltip {
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
}

:deep(.segment-button) {
  border-radius: 8px;
}

.rollout-tooltip strong {
  font-size: 0.9rem;
}

.rollout-tooltip span {
  font-size: 0.78rem;
  line-height: 1.4;
  color: rgba(246, 241, 230, 0.86);
}

@media (max-width: 960px) {
  .rollout-controls {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 680px) {
  .rollout-heading,
  .rollout-slider-meta {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
