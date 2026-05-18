<template>
  <div class="line-chart" :class="{ 'line-chart-ready': chartReady }">
    <div v-if="enablePlayback" class="timeline-toolbar">
      <div class="playback-block">
        <button type="button" class="timeline-button" @click="togglePlayback">
          <span class="timeline-button-icon">{{ isPlaying ? "II" : ">" }}</span>
          {{ isPlaying ? "Pause" : "Play" }}
        </button>

        <div class="timeline-chip">
          <span class="timeline-chip-label">Current</span>
          <strong>{{ revealLabel }}</strong>
        </div>
      </div>

      <label class="timeline-range">
        <span class="timeline-range-label">Timeline focus</span>
        <input
          v-model.number="revealStep"
          class="timeline-slider"
          type="range"
          :min="0"
          :max="maxRevealStep"
          step="1"
          :style="sliderStyle"
        />
      </label>
    </div>

    <div class="legend-row chart-legend">
      <button
        v-for="series in normalizedSeries"
        :key="series.key"
        type="button"
        class="legend-toggle"
        :class="{
          inactive: hiddenKeys.includes(series.key),
          muted: activeSeriesKey && activeSeriesKey !== series.key && !hiddenKeys.includes(series.key),
          active: activeSeriesKey === series.key
        }"
        @click="toggleSeries(series.key)"
        @mouseenter="setActiveSeries(series.key)"
        @mouseleave="clearSeriesHover"
      >
        <span class="legend-swatch" :style="{ background: series.color }"></span>
        {{ series.label }}
      </button>
    </div>

    <div v-if="enablePlayback && playbackStateCards.length" class="state-ribbon">
      <article
        v-for="item in playbackStateCards"
        :key="item.key"
        class="state-card"
        :class="{ active: activeSeriesKey === item.key }"
        @mouseenter="setActiveSeries(item.key)"
        @mouseleave="clearSeriesHover"
      >
        <span class="state-accent" :style="{ background: item.color }"></span>
        <strong>{{ item.label }}</strong>
        <span>{{ item.value }}</span>
      </article>
    </div>

    <div ref="chartWrap" class="chart-surface" @mouseleave="clearTooltip">
      <svg class="chart-svg" :viewBox="`0 0 ${width} ${height}`" role="img" :aria-label="title">
        <g class="chart-grid">
          <line
            v-for="tick in yTicks"
            :key="`y-${tick}`"
            class="grid-line"
            :x1="padding.left"
            :x2="width - padding.right"
            :y1="getY(tick)"
            :y2="getY(tick)"
          />
          <line
            v-if="showZeroLine"
            class="zero-line"
            :x1="padding.left"
            :x2="width - padding.right"
            :y1="getY(0)"
            :y2="getY(0)"
          />
        </g>

        <g>
          <line
            class="axis-line"
            :x1="padding.left"
            :x2="padding.left"
            :y1="padding.top"
            :y2="height - padding.bottom"
          />
          <line
            class="axis-line"
            :x1="padding.left"
            :x2="width - padding.right"
            :y1="height - padding.bottom"
            :y2="height - padding.bottom"
          />
        </g>

        <g>
          <text
            v-for="tick in yTicks"
            :key="`yl-${tick}`"
            class="axis-label"
            :x="padding.left - 10"
            :y="getY(tick) + 4"
            text-anchor="end"
          >
            {{ yTickFormatter(tick) }}
          </text>

          <text
            v-for="tick in xTicks"
            :key="`xl-${tick}`"
            class="axis-label"
            :x="getX(tick)"
            :y="height - padding.bottom + 22"
            text-anchor="middle"
          >
            {{ xTickFormatter(tick) }}
          </text>
        </g>

        <g class="series-layer">
          <g
            v-for="series in renderedSeries"
            :key="series.key"
            class="series-group"
            :class="{
              active: activeSeriesKey === series.key,
              muted: activeSeriesKey && activeSeriesKey !== series.key
            }"
          >
            <path
              class="series-path backdrop"
              :d="getPath(series.points)"
              :stroke="series.color"
              :style="getBackdropStyle(series)"
              @mouseenter="setActiveSeries(series.key)"
            />

            <path
              v-if="series.tailPoints.length > 1"
              class="series-path tail"
              :d="getPath(series.tailPoints)"
              :stroke="series.color"
              :style="getTailStyle(series)"
            />

            <circle
              v-if="series.currentPoint"
              class="series-marker current-marker"
              :cx="getX(series.currentPoint.x)"
              :cy="getY(series.currentPoint.y)"
              :fill="series.color"
              :r="getCurrentMarkerRadius(series)"
              :style="getCurrentMarkerStyle(series)"
            />

            <circle
              v-if="hoveredPointKey.startsWith(`${series.key}::`) && series.hoverPoint"
              class="series-marker hover-marker"
              :cx="getX(series.hoverPoint.x)"
              :cy="getY(series.hoverPoint.y)"
              :fill="series.color"
              :r="series.activeMarkerRadius"
            />

            <circle
              v-for="(point, index) in series.hoverPoints"
              :key="`${series.key}-target-${index}`"
              class="hover-target"
              :cx="getX(point.x)"
              :cy="getY(point.y)"
              :r="hoverRadius"
              @mouseenter="showTooltip($event, series, point)"
              @mousemove="showTooltip($event, series, point)"
            />
          </g>
        </g>

        <text
          class="axis-title"
          :x="(width - padding.left - padding.right) / 2 + padding.left"
          :y="height - 10"
          text-anchor="middle"
        >
          {{ xAxisLabel }}
        </text>

        <text
          class="axis-title"
          :x="18"
          :y="height / 2"
          :transform="`rotate(-90 18 ${height / 2})`"
          text-anchor="middle"
        >
          {{ yAxisLabel }}
        </text>
      </svg>

      <div v-if="tooltip" class="chart-tooltip" :style="{ left: `${tooltip.left}px`, top: `${tooltip.top}px` }">
        <strong>{{ tooltip.title }}</strong>
        <span v-for="(line, index) in tooltip.lines" :key="`${tooltip.title}-${index}`">{{ line }}</span>
      </div>
    </div>

    <div class="story-strip">
      <div class="story-chip">
        <span class="story-kicker">{{ activeSeriesLabel ? "Focus" : "State" }}</span>
        <strong>{{ activeSeriesLabel || revealLabel || title }}</strong>
      </div>
      <p class="story-copy">{{ storyText }}</p>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { clampNumber, formatDateLabel, getLineTicks } from "../../utils/csv";

const props = defineProps({
  title: { type: String, default: "Interactive line chart" },
  series: { type: Array, default: () => [] },
  xAxisLabel: { type: String, default: "" },
  yAxisLabel: { type: String, default: "" },
  xTickFormatter: { type: Function, default: (value) => String(value) },
  yTickFormatter: { type: Function, default: (value) => String(value) },
  tooltipFormatter: {
    type: Function,
    default: (series, point) => ({
      title: series.label,
      lines: [`${point.label}: ${point.y}`]
    })
  },
  showZeroLine: { type: Boolean, default: false },
  enablePlayback: { type: Boolean, default: false },
  playbackLabelFormatter: { type: Function, default: null },
  chartTone: { type: String, default: "default" },
  animateKey: { type: [String, Number], default: "default" }
});

const width = 860;
const height = 380;
const padding = { top: 24, right: 36, bottom: 52, left: 66 };
const hoverRadius = 11;
const hoverStride = 5;
const tailPointCount = 12;

const hiddenKeys = ref([]);
const tooltip = ref(null);
const chartWrap = ref(null);
const activeSeriesKey = ref(null);
const chartReady = ref(false);
const revealStep = ref(0);
const playbackTimer = ref(null);
const hoveredPointKey = ref("");

const toneMap = {
  default: {
    lineWidth: 3.1,
    activeWidth: 5,
    opacity: 0.94,
    mutedOpacity: 0.14,
    markerRadius: 5.8,
    activeMarkerRadius: 7.8
  },
  japan: {
    lineWidth: 3.7,
    activeWidth: 5.8,
    opacity: 0.97,
    mutedOpacity: 0.1,
    markerRadius: 6.2,
    activeMarkerRadius: 8.2
  }
};

const tone = computed(() => toneMap[props.chartTone] || toneMap.default);

const normalizedSeries = computed(() =>
  props.series
    .map((series, index) => ({
      key: series.key ?? series.label ?? `series-${index}`,
      label: series.label ?? `Series ${index + 1}`,
      color: series.color ?? "#1d6b57",
      lineWidth: series.lineWidth ?? tone.value.lineWidth,
      activeLineWidth: series.activeLineWidth ?? tone.value.activeWidth,
      opacity: series.opacity ?? tone.value.opacity,
      mutedOpacity: series.mutedOpacity ?? tone.value.mutedOpacity,
      markerRadius: series.pointRadius ?? tone.value.markerRadius,
      activeMarkerRadius: series.activePointRadius ?? tone.value.activeMarkerRadius,
      points: (series.points || [])
        .filter((point) => Number.isFinite(point.x) && Number.isFinite(point.y))
        .sort((left, right) => left.x - right.x)
    }))
    .filter((series) => series.points.length)
);

watch(
  normalizedSeries,
  (series) => {
    const keys = series.map((item) => item.key);
    hiddenKeys.value = hiddenKeys.value.filter((key) => keys.includes(key));
  },
  { immediate: true }
);

const timelineValues = computed(() => {
  if (!props.enablePlayback) {
    return [];
  }

  return Array.from(
    new Set(
      normalizedSeries.value
        .flatMap((series) => series.points.map((point) => point.x))
        .filter((value) => Number.isFinite(value))
    )
  ).sort((left, right) => left - right);
});

const maxRevealStep = computed(() => Math.max(timelineValues.value.length - 1, 0));
const revealThreshold = computed(() => {
  if (!props.enablePlayback || !timelineValues.value.length) {
    return Number.POSITIVE_INFINITY;
  }
  return timelineValues.value[revealStep.value] ?? timelineValues.value[timelineValues.value.length - 1];
});

const revealLabel = computed(() => {
  if (!props.enablePlayback || !timelineValues.value.length) {
    return "";
  }
  const value = revealThreshold.value;
  if (props.playbackLabelFormatter) {
    return props.playbackLabelFormatter(value, revealStep.value);
  }
  return Number.isFinite(value) ? formatDateLabel(new Date(value).toISOString()) : "";
});

const renderedSeries = computed(() => {
  const threshold = revealThreshold.value;

  return normalizedSeries.value
    .filter((series) => !hiddenKeys.value.includes(series.key))
    .map((series) => {
      const progressedPoints = props.enablePlayback ? series.points.filter((point) => point.x <= threshold) : series.points;
      const currentPoint = progressedPoints.at(-1) || null;
      const tailPoints = progressedPoints.slice(Math.max(0, progressedPoints.length - tailPointCount));
      const hoverPoint = series.points.find((point) => hoveredPointKey.value === `${series.key}::${point.x}::${point.y}`) || null;
      const hoverPoints = series.points.filter((_, index) => index % hoverStride === 0 || index === series.points.length - 1);

      return {
        ...series,
        currentPoint,
        tailPoints,
        hoverPoint,
        hoverPoints
      };
    })
    .filter((series) => series.points.length);
});

const domain = computed(() => {
  const targetSeries = renderedSeries.value.length ? renderedSeries.value : normalizedSeries.value;
  const xs = targetSeries.flatMap((series) => series.points.map((point) => point.x));
  const ys = targetSeries.flatMap((series) => series.points.map((point) => point.y));

  const xMin = Math.min(...xs);
  const xMax = Math.max(...xs);
  const rawYMin = Math.min(...ys);
  const rawYMax = Math.max(...ys);
  const yMin = props.showZeroLine ? Math.min(0, rawYMin) : rawYMin;
  const yMax = props.showZeroLine ? Math.max(0, rawYMax) : rawYMax;
  const yPad = (yMax - yMin || 1) * 0.12;

  return {
    xMin: Number.isFinite(xMin) ? xMin : 0,
    xMax: Number.isFinite(xMax) ? xMax : 1,
    yMin: Number.isFinite(yMin) ? yMin - yPad : 0,
    yMax: Number.isFinite(yMax) ? yMax + yPad : 1
  };
});

const xTicks = computed(() => getLineTicks(domain.value.xMin, domain.value.xMax, 6));
const yTicks = computed(() => getLineTicks(domain.value.yMin, domain.value.yMax, 5));

const activeSeriesLabel = computed(
  () => renderedSeries.value.find((series) => series.key === activeSeriesKey.value)?.label || ""
);

const playbackStateCards = computed(() =>
  renderedSeries.value
    .filter((series) => series.currentPoint)
    .sort((left, right) => right.currentPoint.y - left.currentPoint.y)
    .slice(0, 4)
    .map((series) => ({
      key: series.key,
      label: series.label,
      color: series.color,
      value: formatValue(series.currentPoint.y)
    }))
);

const storyText = computed(() => {
  if (activeSeriesKey.value) {
    const series = renderedSeries.value.find((item) => item.key === activeSeriesKey.value);
    if (series?.currentPoint) {
      return `${series.label} is in focus. The thick foreground segment shows the recent trajectory only, while the rest of the history stays as faint context.`;
    }
  }

  if (props.enablePlayback && playbackStateCards.value.length) {
    return `At ${revealLabel.value}, the leading visible states are ${playbackStateCards.value
      .map((item) => `${item.label} (${item.value})`)
      .join(", ")}.`;
  }

  return "The background keeps the full trajectory readable, while the animated layer only moves the current state and short recent tail.";
});

const sliderStyle = computed(() => {
  const progress = maxRevealStep.value <= 0 ? 100 : (revealStep.value / maxRevealStep.value) * 100;
  return {
    background: `linear-gradient(90deg, #1d6b57 0%, #2e7b66 ${progress}%, rgba(31, 42, 31, 0.12) ${progress}%, rgba(31, 42, 31, 0.12) 100%)`
  };
});

const isPlaying = computed(() => playbackTimer.value !== null);

watch(
  () => props.animateKey,
  () => {
    chartReady.value = false;
    requestAnimationFrame(() => {
      chartReady.value = true;
    });
  },
  { immediate: true }
);

watch(
  timelineValues,
  (values) => {
    if (props.enablePlayback) {
      revealStep.value = values.length ? 0 : 0;
    }
  },
  { immediate: true }
);

onMounted(() => {
  chartReady.value = true;
});

onBeforeUnmount(() => {
  stopPlayback();
});

function getX(value) {
  const { xMin, xMax } = domain.value;
  const plotWidth = width - padding.left - padding.right;
  if (xMax === xMin) {
    return padding.left + plotWidth / 2;
  }
  return padding.left + ((value - xMin) / (xMax - xMin)) * plotWidth;
}

function getY(value) {
  const { yMin, yMax } = domain.value;
  const plotHeight = height - padding.top - padding.bottom;
  if (yMax === yMin) {
    return padding.top + plotHeight / 2;
  }
  return height - padding.bottom - ((value - yMin) / (yMax - yMin)) * plotHeight;
}

function getPath(points) {
  if (!points.length) {
    return "";
  }
  return points
    .map((point, index) => `${index === 0 ? "M" : "L"} ${getX(point.x).toFixed(2)} ${getY(point.y).toFixed(2)}`)
    .join(" ");
}

function getBackdropStyle(series) {
  const isActive = activeSeriesKey.value === series.key;
  const isMuted = activeSeriesKey.value && activeSeriesKey.value !== series.key;
  return {
    opacity: isMuted ? 0.08 : isActive ? 0.24 : 0.18,
    strokeWidth: `${Math.max(series.lineWidth - 0.8, 2)}px`
  };
}

function getTailStyle(series) {
  const isActive = activeSeriesKey.value === series.key;
  const isMuted = activeSeriesKey.value && activeSeriesKey.value !== series.key;
  return {
    opacity: isMuted ? 0.15 : series.opacity,
    strokeWidth: `${isActive ? series.activeLineWidth : series.lineWidth}px`
  };
}

function getCurrentMarkerRadius(series) {
  return activeSeriesKey.value === series.key ? series.activeMarkerRadius : series.markerRadius;
}

function getCurrentMarkerStyle(series) {
  const isMuted = activeSeriesKey.value && activeSeriesKey.value !== series.key;
  return {
    opacity: isMuted ? 0.24 : 0.98
  };
}

function toggleSeries(key) {
  hiddenKeys.value = hiddenKeys.value.includes(key)
    ? hiddenKeys.value.filter((item) => item !== key)
    : [...hiddenKeys.value, key];
  tooltip.value = null;
}

function setActiveSeries(key) {
  activeSeriesKey.value = key;
}

function clearSeriesHover() {
  if (!tooltip.value) {
    activeSeriesKey.value = null;
  }
}

function showTooltip(event, series, point) {
  const bounds = chartWrap.value?.getBoundingClientRect();
  if (!bounds) {
    return;
  }

  activeSeriesKey.value = series.key;
  hoveredPointKey.value = `${series.key}::${point.x}::${point.y}`;
  const formatted = props.tooltipFormatter(series, point);
  const lines = Array.isArray(formatted.lines) ? formatted.lines : formatted.body ? [formatted.body] : [];

  tooltip.value = {
    title: formatted.title,
    lines,
    left: clampNumber(event.clientX - bounds.left + 14, 12, bounds.width - 238),
    top: clampNumber(event.clientY - bounds.top - 10, 12, bounds.height - 112)
  };
}

function clearTooltip() {
  tooltip.value = null;
  hoveredPointKey.value = "";
  activeSeriesKey.value = null;
}

function togglePlayback() {
  if (isPlaying.value) {
    stopPlayback();
    return;
  }

  if (revealStep.value >= maxRevealStep.value) {
    revealStep.value = 0;
  }

  playbackTimer.value = window.setInterval(() => {
    revealStep.value = Math.min(revealStep.value + 1, maxRevealStep.value);
    if (revealStep.value >= maxRevealStep.value) {
      stopPlayback();
    }
  }, 220);
}

function stopPlayback() {
  if (playbackTimer.value !== null) {
    clearInterval(playbackTimer.value);
    playbackTimer.value = null;
  }
}

function formatValue(value) {
  return Number.isFinite(value) ? value.toFixed(1) : "N/A";
}
</script>

<style scoped>
.line-chart {
  display: grid;
  gap: 0.95rem;
}

.timeline-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  padding: 0.85rem 0.95rem;
  border-radius: 16px;
  background: linear-gradient(180deg, rgba(242, 230, 211, 0.72), rgba(255, 250, 242, 0.9));
  border: 1px solid rgba(31, 42, 31, 0.08);
}

.playback-block {
  display: flex;
  align-items: center;
  gap: 0.72rem;
}

.timeline-button {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  border: 1px solid rgba(29, 107, 87, 0.28);
  background: linear-gradient(180deg, #27584b 0%, #1d6b57 100%);
  color: #fffaf2;
  border-radius: 999px;
  padding: 0.54rem 0.96rem;
  cursor: pointer;
  font: inherit;
  font-weight: 600;
  box-shadow: 0 10px 20px rgba(29, 107, 87, 0.14);
}

.timeline-button-icon {
  width: 1rem;
  display: inline-flex;
  justify-content: center;
  font-size: 0.78rem;
}

.timeline-chip {
  display: grid;
  gap: 0.12rem;
  padding: 0.42rem 0.72rem;
  border-radius: 12px;
  background: rgba(255, 250, 242, 0.94);
  border: 1px solid rgba(31, 42, 31, 0.08);
}

.timeline-chip-label,
.timeline-range-label {
  color: var(--muted);
  font-size: 0.78rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.timeline-chip strong {
  font-size: 0.98rem;
}

.timeline-range {
  display: grid;
  gap: 0.35rem;
  min-width: 300px;
}

.timeline-slider {
  appearance: none;
  width: 100%;
  height: 8px;
  border-radius: 999px;
  outline: none;
}

.timeline-slider::-webkit-slider-thumb {
  appearance: none;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #fffaf2;
  border: 3px solid #1d6b57;
  box-shadow: 0 4px 12px rgba(29, 107, 87, 0.2);
  cursor: pointer;
}

.timeline-slider::-moz-range-thumb {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #fffaf2;
  border: 3px solid #1d6b57;
  box-shadow: 0 4px 12px rgba(29, 107, 87, 0.2);
  cursor: pointer;
}

.chart-legend {
  gap: 0.55rem;
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
  transition: opacity 0.24s ease, transform 0.24s ease, border-color 0.24s ease;
}

.legend-toggle.active {
  transform: translateY(-1px);
  border-color: rgba(29, 107, 87, 0.32);
}

.legend-toggle.muted {
  opacity: 0.52;
}

.legend-toggle.inactive {
  opacity: 0.3;
}

.state-ribbon {
  display: grid;
  gap: 0.75rem;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
}

.state-card {
  display: grid;
  grid-template-columns: 10px 1fr;
  gap: 0.45rem 0.7rem;
  align-items: center;
  padding: 0.72rem 0.8rem;
  border-radius: 16px;
  background: rgba(242, 230, 211, 0.42);
  border: 1px solid rgba(31, 42, 31, 0.08);
}

.state-card.active {
  background: rgba(255, 250, 242, 0.9);
  border-color: rgba(29, 107, 87, 0.18);
}

.state-accent {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  grid-row: 1 / span 2;
  align-self: center;
}

.state-card strong {
  font-size: 0.95rem;
}

.state-card span:last-child {
  color: var(--muted);
  font-size: 0.9rem;
}

.chart-surface {
  position: relative;
  border-radius: 18px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.92), rgba(249, 243, 233, 0.99));
  border: 1px solid rgba(31, 42, 31, 0.08);
  padding: 0.45rem;
  overflow: hidden;
}

.chart-surface::before {
  content: "";
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at top right, rgba(29, 107, 87, 0.04), transparent 30%);
  pointer-events: none;
}

.grid-line {
  stroke: rgba(31, 42, 31, 0.06);
  stroke-width: 1;
}

.zero-line {
  stroke: rgba(184, 92, 56, 0.58);
  stroke-width: 1.5;
  stroke-dasharray: 6 6;
}

.series-group {
  transition: opacity 0.24s ease;
}

.series-group.muted {
  opacity: 0.62;
}

.series-path {
  fill: none;
  stroke-linecap: round;
  stroke-linejoin: round;
  transition: opacity 0.24s ease, stroke-width 0.24s ease;
}

.series-path.backdrop {
  filter: saturate(0.88);
}

.series-marker {
  stroke: rgba(255, 250, 242, 0.98);
  stroke-width: 2;
  transition: opacity 0.24s ease, r 0.24s ease;
}

.current-marker {
  filter: drop-shadow(0 4px 10px rgba(31, 42, 31, 0.16));
}

.hover-target {
  fill: transparent;
  pointer-events: all;
}

.line-chart-ready .series-path.tail,
.line-chart-ready .current-marker {
  animation: chart-enter 0.54s ease both;
}

.chart-tooltip {
  position: absolute;
  display: grid;
  gap: 0.18rem;
  min-width: 170px;
  max-width: 240px;
  pointer-events: none;
  padding: 0.76rem 0.84rem;
  border-radius: 14px;
  background: rgba(24, 54, 47, 0.96);
  color: #f7efe1;
  box-shadow: 0 14px 32px rgba(24, 54, 47, 0.22);
}

.chart-tooltip strong,
.chart-tooltip span {
  font-size: 0.86rem;
  line-height: 1.35;
}

.story-strip {
  display: grid;
  gap: 0.45rem;
  padding: 0.82rem 0.92rem;
  border-radius: 16px;
  background: rgba(242, 230, 211, 0.46);
  border: 1px solid rgba(31, 42, 31, 0.07);
}

.story-chip {
  display: inline-flex;
  align-items: baseline;
  gap: 0.55rem;
  width: fit-content;
}

.story-kicker {
  color: var(--accent-2);
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.story-chip strong {
  color: var(--ink);
  font-size: 0.98rem;
}

.story-copy {
  margin: 0;
  color: var(--muted);
  line-height: 1.55;
  font-size: 0.95rem;
}

@keyframes chart-enter {
  0% {
    opacity: 0;
    transform: translateY(4px);
  }

  100% {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 960px) {
  .timeline-toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .timeline-range {
    min-width: 0;
    width: 100%;
  }

  .state-ribbon {
    grid-template-columns: 1fr;
  }
}
</style>
