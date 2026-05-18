<template>
  <div class="bar-chart">
    <div class="legend-row chart-legend">
      <button
        v-for="series in normalizedSeries"
        :key="series.key"
        type="button"
        class="legend-toggle"
        :class="{ inactive: hiddenKeys.includes(series.key) }"
        @click="toggleSeries(series.key)"
      >
        <span class="legend-swatch" :style="{ background: series.color }"></span>
        {{ series.label }}
      </button>
    </div>

    <div ref="chartWrap" class="chart-surface" @mouseleave="clearTooltip">
      <svg class="chart-svg" :viewBox="`0 0 ${width} ${chartHeight}`" role="img" :aria-label="title">
        <g>
          <line
            v-for="tick in xTicks"
            :key="`x-${tick}`"
            class="grid-line"
            :x1="getX(tick)"
            :x2="getX(tick)"
            :y1="padding.top"
            :y2="chartHeight - padding.bottom"
          />
        </g>

        <line
          class="axis-line"
          :x1="padding.left"
          :x2="padding.left"
          :y1="padding.top"
          :y2="chartHeight - padding.bottom"
        />
        <line
          class="axis-line"
          :x1="padding.left"
          :x2="width - padding.right"
          :y1="chartHeight - padding.bottom"
          :y2="chartHeight - padding.bottom"
        />

        <g>
          <text
            v-for="tick in xTicks"
            :key="`xl-${tick}`"
            class="axis-label"
            :x="getX(tick)"
            :y="chartHeight - padding.bottom + 22"
            text-anchor="middle"
          >
            {{ yTickFormatter(tick) }}
          </text>
        </g>

        <g v-for="(category, categoryIndex) in categories" :key="category">
          <text
            class="axis-label category-label"
            :x="padding.left - 12"
            :y="getCategoryCenter(categoryIndex) + 4"
            text-anchor="end"
          >
            {{ category }}
          </text>

          <rect
            v-for="bar in getBarsForCategory(categoryIndex)"
            :key="`${category}-${bar.key}`"
            class="bar-rect"
            :x="padding.left"
            :y="bar.y"
            :width="bar.width"
            :height="bar.height"
            :fill="bar.color"
            rx="0"
            ry="0"
            @mouseenter="showTooltip($event, category, bar)"
            @mousemove="showTooltip($event, category, bar)"
          />
        </g>

        <text
          class="axis-title"
          :x="(width - padding.left - padding.right) / 2 + padding.left"
          :y="chartHeight - 10"
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
  </div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { clampNumber, getLineTicks } from "../../utils/csv";

const props = defineProps({
  title: { type: String, default: "Interactive grouped bar chart" },
  categories: { type: Array, default: () => [] },
  series: { type: Array, default: () => [] },
  xAxisLabel: { type: String, default: "" },
  yAxisLabel: { type: String, default: "" },
  yTickFormatter: { type: Function, default: (value) => String(value) },
  tooltipFormatter: {
    type: Function,
    default: (category, bar) => ({
      title: `${category} ${bar.label}`,
      lines: [`${bar.value}`]
    })
  }
});

const width = 900;
const padding = { top: 24, right: 30, bottom: 60, left: 150 };
const categoryBand = 72;

const hiddenKeys = ref([]);
const tooltip = ref(null);
const chartWrap = ref(null);

const normalizedSeries = computed(() =>
  props.series.map((series, index) => ({
    key: series.key ?? series.label ?? `series-${index}`,
    label: series.label ?? `Series ${index + 1}`,
    color: series.color ?? "#1d6b57",
    values: props.categories.map((_, categoryIndex) => {
      const rawValue = series.values?.[categoryIndex];
      return Number.isFinite(rawValue) ? rawValue : null;
    })
  }))
);

watch(
  normalizedSeries,
  (series) => {
    const keys = series.map((item) => item.key);
    hiddenKeys.value = hiddenKeys.value.filter((key) => keys.includes(key));
  },
  { immediate: true }
);

const visibleSeries = computed(() => normalizedSeries.value.filter((series) => !hiddenKeys.value.includes(series.key)));

const chartHeight = computed(() => padding.top + padding.bottom + Math.max(props.categories.length, 1) * categoryBand);

const xDomain = computed(() => {
  const targetSeries = visibleSeries.value.length ? visibleSeries.value : normalizedSeries.value;
  const values = targetSeries.flatMap((series) => series.values.filter((value) => Number.isFinite(value)));
  const max = Math.max(...values, 0);
  return {
    min: 0,
    max: max > 0 ? max * 1.12 : 1
  };
});

const xTicks = computed(() => getLineTicks(xDomain.value.min, xDomain.value.max, 5));

function getX(value) {
  const plotWidth = width - padding.left - padding.right;
  return padding.left + ((value - xDomain.value.min) / (xDomain.value.max - xDomain.value.min || 1)) * plotWidth;
}

function getCategoryCenter(index) {
  return padding.top + categoryBand * index + categoryBand / 2;
}

function getBarsForCategory(categoryIndex) {
  const series = visibleSeries.value;
  const activeCount = Math.max(series.length, 1);
  const totalBand = 44;
  const innerGap = Math.min(8, totalBand * 0.12);
  const barHeight = Math.max(10, (totalBand - innerGap * (activeCount - 1)) / activeCount);
  const startY = getCategoryCenter(categoryIndex) - totalBand / 2;

  return series
    .map((item, seriesIndex) => {
      const value = item.values[categoryIndex];
      if (!Number.isFinite(value)) {
        return null;
      }

      return {
        key: item.key,
        label: item.label,
        color: item.color,
        value,
        y: startY + seriesIndex * (barHeight + innerGap),
        width: Math.max(0, getX(value) - padding.left),
        height: barHeight
      };
    })
    .filter(Boolean);
}

function toggleSeries(key) {
  hiddenKeys.value = hiddenKeys.value.includes(key)
    ? hiddenKeys.value.filter((item) => item !== key)
    : [...hiddenKeys.value, key];
  tooltip.value = null;
}

function showTooltip(event, category, bar) {
  const bounds = chartWrap.value?.getBoundingClientRect();
  if (!bounds) {
    return;
  }

  const formatted = props.tooltipFormatter(category, bar);
  tooltip.value = {
    title: formatted.title,
    lines: Array.isArray(formatted.lines) ? formatted.lines : formatted.body ? [formatted.body] : [],
    left: clampNumber(event.clientX - bounds.left + 14, 12, bounds.width - 220),
    top: clampNumber(event.clientY - bounds.top - 12, 12, bounds.height - 76)
  };
}

function clearTooltip() {
  tooltip.value = null;
}
</script>

<style scoped>
.bar-chart {
  display: grid;
  gap: 0.8rem;
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
  transition: opacity 0.24s ease, transform 0.24s ease;
}

.legend-toggle.inactive {
  opacity: 0.45;
}

.chart-surface {
  position: relative;
  border-radius: 18px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.82), rgba(250, 244, 234, 0.96));
  border: 1px solid rgba(31, 42, 31, 0.08);
  padding: 0.45rem;
  overflow: hidden;
}

.bar-rect {
  transition: opacity 0.24s ease, transform 0.24s ease;
  animation: bar-enter 0.55s ease both;
  transform-origin: left center;
}

.bar-rect:hover {
  opacity: 0.92;
  transform: translateX(2px);
}

.category-label {
  font-size: 10px;
}

.chart-tooltip {
  position: absolute;
  display: grid;
  gap: 0.2rem;
  min-width: 150px;
  max-width: 220px;
  pointer-events: none;
  padding: 0.65rem 0.75rem;
  border-radius: 12px;
  background: rgba(24, 54, 47, 0.94);
  color: #f7efe1;
  box-shadow: 0 12px 28px rgba(24, 54, 47, 0.22);
}

.chart-tooltip strong,
.chart-tooltip span {
  font-size: 0.86rem;
  line-height: 1.35;
}

@keyframes bar-enter {
  0% {
    opacity: 0;
    transform: scaleX(0.92);
  }

  100% {
    opacity: 1;
    transform: scaleX(1);
  }
}
</style>
