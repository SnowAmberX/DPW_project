<template>
  <div v-if="bubbleFrameMonths.length" class="bubble-shell">
    <div class="bubble-heading">
      <div>
        <p class="bubble-kicker">Interactive overview</p>
        <h4>Monthly movement in the vaccination–cases space</h4>
      </div>
      <div class="month-badge">{{ selectedBubbleMonth }}</div>
    </div>

    <div class="bubble-chart-card">
      <svg class="bubble-chart" viewBox="0 0 960 530" role="img" aria-label="Animated vaccination and case scatter plot">
        <g>
          <line
            v-for="tick in bubbleYAxisTicks"
            :key="`y-${tick.value}`"
            :x1="bubbleChartBounds.left"
            :x2="bubbleChartBounds.right"
            :y1="tick.y"
            :y2="tick.y"
            class="bubble-grid"
          />
          <line
            v-for="tick in bubbleXAxisTicks"
            :key="`x-${tick.value}`"
            :x1="tick.x"
            :x2="tick.x"
            :y1="bubbleChartBounds.top"
            :y2="bubbleChartBounds.bottom"
            class="bubble-grid bubble-grid-vertical"
          />
        </g>

        <line
          :x1="bubbleChartBounds.left"
          :x2="bubbleChartBounds.right"
          :y1="bubbleChartBounds.bottom"
          :y2="bubbleChartBounds.bottom"
          class="bubble-axis"
        />
        <line
          :x1="bubbleChartBounds.left"
          :x2="bubbleChartBounds.left"
          :y1="bubbleChartBounds.top"
          :y2="bubbleChartBounds.bottom"
          class="bubble-axis"
        />

        <text
          v-for="tick in bubbleYAxisTicks"
          :key="`yl-${tick.value}`"
          :x="bubbleChartBounds.left - 14"
          :y="tick.y + 5"
          text-anchor="end"
          class="bubble-tick"
        >
          {{ tick.label }}
        </text>
        <text
          v-for="tick in bubbleXAxisTicks"
          :key="`xl-${tick.value}`"
          :x="tick.x"
          :y="bubbleChartBounds.bottom + 30"
          text-anchor="middle"
          class="bubble-tick"
        >
          {{ tick.label }}
        </text>

        <text
          :x="(bubbleChartBounds.left + bubbleChartBounds.right) / 2"
          :y="506"
          text-anchor="middle"
          class="bubble-axis-label"
        >
          People vaccinated (% of population)
        </text>
        <text
          :x="30"
          :y="(bubbleChartBounds.top + bubbleChartBounds.bottom) / 2"
          transform="rotate(-90 30 252)"
          text-anchor="middle"
          class="bubble-axis-label"
        >
          7-day avg new cases per million, log scale
        </text>

        <g>
          <g
            v-for="point in selectedBubbleFrame"
            :key="`${selectedBubbleMonth}-${point.country}`"
            class="bubble-point-group"
            :style="{ '--bubble-color': point.color }"
            @mouseenter="showTooltip($event, point)"
            @mousemove="moveTooltip($event)"
            @mouseleave="hideTooltip"
          >
            <circle
              class="bubble-shadow"
              :cx="bubbleX(point.vaccinationRate)"
              :cy="bubbleY(point.caseRate)"
              :r="bubbleRadius(point.casePressure) + 5"
            />
            <circle
              class="bubble-point"
              :cx="bubbleX(point.vaccinationRate)"
              :cy="bubbleY(point.caseRate)"
              :r="bubbleRadius(point.casePressure)"
            />
            <text
              :x="bubbleX(point.vaccinationRate)"
              :y="bubbleY(point.caseRate) - bubbleRadius(point.casePressure) - 13"
              text-anchor="middle"
              class="bubble-label"
            >
              {{ point.country }}
            </text>
          </g>
        </g>
      </svg>
    </div>

    <div class="bubble-controls">
      <div class="bubble-actions">
        <button type="button" class="bubble-btn bubble-btn-active" @click="startPlayback">Play</button>
        <button type="button" class="bubble-btn" @click="stopPlayback">Pause</button>
        <button type="button" class="bubble-btn" :class="{ selected: speedMode === '1x' }" @click="setSpeed('1x')">1x</button>
        <button type="button" class="bubble-btn" :class="{ selected: speedMode === '2x' }" @click="setSpeed('2x')">2x</button>
      </div>
      <div class="bubble-slider-block">
        <div class="bubble-slider-meta">
          <strong>Month</strong>
          <span>{{ selectedBubbleMonth }}</span>
        </div>
        <input
          v-model.number="selectedBubbleMonthIndex"
          type="range"
          min="0"
          :max="Math.max(0, bubbleFrameMonths.length - 1)"
        />
        <div class="bubble-month-rail">
          <span v-for="month in bubbleVisibleMonthTicks" :key="month">{{ month }}</span>
        </div>
      </div>
    </div>

    <p class="bubble-note">
      Each bubble represents one country-month. Moving right means vaccination coverage increases; moving upward or
      becoming larger means case pressure rises.
    </p>

    <div v-if="tooltip" class="bubble-tooltip" :style="{ left: `${tooltip.x}px`, top: `${tooltip.y}px` }">
      <strong>{{ tooltip.title }}</strong>
      <span v-for="line in tooltip.lines" :key="line">{{ line }}</span>
    </div>
  </div>

  <p v-else class="bubble-empty">The interactive bubble chart is unavailable because the source file could not be loaded.</p>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { loadCsvFromCandidates, pickField, toNumber } from "../utils/csv";

const rows = ref([]);
const tooltip = ref(null);
const selectedBubbleMonthIndex = ref(0);
const speedMode = ref("2x");
const analysisEndDate = new Date("2023-12-31T23:59:59.999Z");
let playbackTimer = null;

const bubbleChartBounds = {
  left: 84,
  right: 860,
  top: 48,
  bottom: 424,
};

const speedDelay = computed(() => (speedMode.value === "2x" ? 160 : 460));

onMounted(async () => {
  const dataset = await loadCsvFromCandidates(["merged_cases_vaccination_4countries.csv"], "/analysis/cases-vaccination");
  rows.value = dataset.rows.filter((row) => {
    const date = pickField(row, ["date", "Date"]);
    const dateObject = new Date(date);
    return !Number.isNaN(dateObject.getTime()) && dateObject <= analysisEndDate;
  });
  selectedBubbleMonthIndex.value = 0;
});

onBeforeUnmount(() => {
  stopPlayback();
});

const bubbleSeriesRows = computed(() =>
  rows.value
    .map((row) => {
      const date = pickField(row, ["date", "Date"]);
      const dateObject = new Date(date);
      if (Number.isNaN(dateObject.getTime()) || dateObject > analysisEndDate) {
        return null;
      }

      const caseRate = toNumber(pickField(row, ["new_cases_pm_7d", "new_cases_pm_7d_after_0d"]));
      const casePressure = toNumber(pickField(row, ["new_cases_per_million", "new_cases_pm_7d"]));

      return {
        country: pickField(row, ["country", "location"]),
        monthKey: `${dateObject.getUTCFullYear()}-${String(dateObject.getUTCMonth() + 1).padStart(2, "0")}`,
        vaccinationRate: toNumber(pickField(row, ["vaccination_rate"])),
        caseRate: Number.isFinite(caseRate) ? caseRate : 0,
        casePressure: Number.isFinite(casePressure) ? casePressure : 0,
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
    if (!monthMap[row.monthKey]) {
      monthMap[row.monthKey] = {};
    }
    monthMap[row.monthKey][row.country] = row;
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

const bubbleYMaxLog = computed(() => {
  const max = Math.max(...bubbleSeriesRows.value.map((row) => Math.log10(Math.max(row.caseRate, 0) + 1)), 0);
  return max > 0 ? Math.ceil(max * 10) / 10 : 1;
});

const bubblePressureMax = computed(() => Math.max(...bubbleSeriesRows.value.map((row) => Math.log10(Math.max(row.casePressure, 0) + 1)), 0));
const bubbleXAxisTicks = computed(() => [0, 20, 40, 60, 80, 100].map((value) => ({ value, label: `${value}`, x: bubbleX(value) })));
const bubbleYAxisTicks = computed(() =>
  [0, 10, 100, 1000, 3000]
    .filter((value) => Math.log10(value + 1) <= bubbleYMaxLog.value + 0.05)
    .map((value) => ({
      value,
      label: value >= 1000 ? `${Math.round(value / 1000)}k` : `${value}`,
      y: bubbleY(value),
    }))
);

const bubbleVisibleMonthTicks = computed(() => {
  if (bubbleFrameMonths.value.length <= 6) {
    return bubbleFrameMonths.value;
  }
  const step = Math.ceil(bubbleFrameMonths.value.length / 6);
  return bubbleFrameMonths.value.filter((_, index) => index % step === 0 || index === bubbleFrameMonths.value.length - 1);
});

function bubbleX(value) {
  const ratio = Math.max(0, Math.min(1, value / 100));
  return bubbleChartBounds.left + ratio * (bubbleChartBounds.right - bubbleChartBounds.left);
}

function bubbleY(value) {
  const max = bubbleYMaxLog.value || 1;
  const logValue = Math.log10(Math.max(value, 0) + 1);
  const ratio = Math.max(0, Math.min(1, logValue / max));
  return bubbleChartBounds.bottom - ratio * (bubbleChartBounds.bottom - bubbleChartBounds.top);
}

function bubbleRadius(value) {
  const max = bubblePressureMax.value || 1;
  const logValue = Math.log10(Math.max(value, 0) + 1);
  const ratio = Math.max(0, Math.min(1, logValue / max));
  return 13 + ratio * 29;
}

function bubbleColor(country) {
  const palette = {
    China: "#4e8b79",
    "United States": "#1f7a6b",
    India: "#c06a42",
    Japan: "#9b8b6d",
  };
  return palette[country] || "#6ea58a";
}

function startPlayback() {
  if (playbackTimer || bubbleFrameMonths.value.length <= 1) {
    return;
  }
  playbackTimer = window.setInterval(() => {
    if (selectedBubbleMonthIndex.value >= bubbleFrameMonths.value.length - 1) {
      selectedBubbleMonthIndex.value = 0;
      return;
    }
    selectedBubbleMonthIndex.value += 1;
  }, speedDelay.value);
}

function stopPlayback() {
  if (!playbackTimer) {
    return;
  }
  window.clearInterval(playbackTimer);
  playbackTimer = null;
}

function setSpeed(speed) {
  speedMode.value = speed;
  if (playbackTimer) {
    stopPlayback();
    startPlayback();
  }
}

function showTooltip(event, point) {
  tooltip.value = {
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
</script>

<style scoped>
.bubble-shell {
  display: grid;
  gap: 1rem;
}

.bubble-heading {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
}

.bubble-kicker {
  margin: 0 0 0.35rem;
  color: #c06a42;
  font-size: 0.74rem;
  font-weight: 800;
  letter-spacing: 0.11em;
  text-transform: uppercase;
}

.bubble-heading h4 {
  margin: 0;
  color: #23362f;
  font-size: 1.28rem;
  line-height: 1.24;
}

.month-badge {
  padding: 0.55rem 0.85rem;
  border-radius: 999px;
  color: #23362f;
  background: rgba(255, 255, 255, 0.78);
  border: 1px solid rgba(207, 198, 183, 0.88);
  font-size: 0.88rem;
  font-weight: 800;
  white-space: nowrap;
}

.bubble-chart-card {
  padding: 0.85rem 0.95rem 0.6rem;
  border-radius: 24px;
  background: linear-gradient(180deg, rgba(255, 252, 247, 0.94) 0%, rgba(249, 245, 237, 0.96) 100%);
  border: 1px solid rgba(31, 42, 31, 0.08);
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
  stroke: rgba(31, 42, 31, 0.26);
  stroke-width: 1.3;
}

.bubble-tick {
  fill: #627168;
  font-size: 12px;
}

.bubble-axis-label {
  fill: #304238;
  font-size: 14px;
  font-weight: 700;
}

.bubble-point-group {
  cursor: pointer;
}

.bubble-shadow {
  fill: var(--bubble-color);
  fill-opacity: 0.14;
  transition:
    cx 0.2s ease,
    cy 0.2s ease,
    r 0.2s ease;
}

.bubble-point {
  fill: var(--bubble-color);
  fill-opacity: 0.84;
  stroke: rgba(255, 255, 255, 0.96);
  stroke-width: 2.4;
  transition:
    cx 0.2s ease,
    cy 0.2s ease,
    r 0.2s ease,
    transform 0.16s ease,
    fill-opacity 0.16s ease;
}

.bubble-point-group:hover .bubble-point {
  fill-opacity: 0.98;
  transform: scale(1.04);
}

.bubble-label {
  fill: #23362f;
  font-size: 13px;
  font-weight: 800;
  paint-order: stroke;
  stroke: rgba(247, 244, 238, 0.9);
  stroke-width: 3px;
  pointer-events: none;
}

.bubble-controls {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 1rem;
  align-items: center;
}

.bubble-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
}

.bubble-btn {
  min-width: 68px;
  height: 40px;
  border-radius: 999px;
  border: 1px solid rgba(31, 42, 31, 0.12);
  background: rgba(255, 255, 255, 0.78);
  color: #304238;
  font-weight: 700;
  cursor: pointer;
}

.bubble-btn-active,
.bubble-btn.selected {
  background: linear-gradient(135deg, #1f7a6b, #318c79);
  color: #fffaf2;
  border-color: transparent;
}

.bubble-slider-block {
  display: grid;
  gap: 0.48rem;
}

.bubble-slider-meta {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: center;
  color: #23362f;
}

.bubble-slider-block input {
  accent-color: #1f7a6b;
}

.bubble-month-rail {
  display: flex;
  justify-content: space-between;
  gap: 0.5rem;
  color: #627168;
  font-size: 0.72rem;
}

.bubble-note,
.bubble-empty {
  margin: 0;
  color: #627168;
  line-height: 1.58;
}

.bubble-tooltip {
  position: fixed;
  z-index: 40;
  display: grid;
  gap: 0.16rem;
  max-width: 250px;
  padding: 0.72rem 0.8rem;
  border-radius: 14px;
  background: rgba(26, 45, 38, 0.95);
  color: #f6f1e6;
  box-shadow: 0 18px 34px rgba(18, 30, 25, 0.22);
  pointer-events: none;
}

.bubble-tooltip strong {
  font-size: 0.9rem;
}

.bubble-tooltip span {
  font-size: 0.78rem;
  line-height: 1.4;
  color: rgba(246, 241, 230, 0.86);
}

@media (max-width: 860px) {
  .bubble-controls {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 680px) {
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
