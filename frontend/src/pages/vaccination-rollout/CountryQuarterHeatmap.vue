<template>
  <div class="quarter-heatmap">
    <div class="heatmap-controls">
      <div class="heat-legend">
        <span>{{ metricLabel }}</span>
        <span class="heat-legend-bar" :style="{ background: legendGradient }"></span>
        <span>{{ minLabel }}</span>
        <span>{{ maxLabel }}</span>
      </div>
    </div>

    <div class="heatmap-wrap">
      <div class="heatmap-head" :style="gridStyle">
        <span>Country</span>
        <span v-for="quarter in quarters" :key="quarter">{{ quarter }}</span>
      </div>

      <div v-for="country in countries" :key="country" class="heatmap-row" :style="gridStyle">
        <strong>{{ country }}</strong>
        <button
          v-for="quarter in quarters"
          :key="`${country}-${quarter}`"
          type="button"
          class="heat-cell"
          :style="{ background: colorFor(getCell(country, quarter)?.value) }"
          :aria-label="ariaLabel(country, quarter)"
          @mouseenter="activeCell = getCell(country, quarter) || null"
          @focus="activeCell = getCell(country, quarter) || null"
          @mouseleave="activeCell = null"
          @blur="activeCell = null"
        ></button>
      </div>
    </div>

    <div class="heatmap-active">
      <p v-if="activeCell">
        <strong>{{ activeCell.country }}</strong>
        <span>{{ activeCell.quarter }}</span>
        <span>{{ formatValue(activeCell.value) }}</span>
      </p>
      <p v-else>Hover a cell to inspect the quarter-level value for each country.</p>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from "vue";

const props = defineProps({
  countries: {
    type: Array,
    default: () => []
  },
  quarters: {
    type: Array,
    default: () => []
  },
  cells: {
    type: Array,
    default: () => []
  },
  metricLabel: {
    type: String,
    default: ""
  },
  valueFormatter: {
    type: Function,
    default: (value) => String(value ?? "")
  }
});

const activeCell = ref(null);

const cellMap = computed(() =>
  props.cells.reduce((map, cell) => {
    map[`${cell.country}__${cell.quarter}`] = cell;
    return map;
  }, {})
);

const values = computed(() => props.cells.map((cell) => cell.value).filter((value) => Number.isFinite(value)));
const minValue = computed(() => (values.value.length ? Math.min(...values.value) : 0));
const maxValue = computed(() => (values.value.length ? Math.max(...values.value) : 1));

const minLabel = computed(() => formatValue(minValue.value));
const maxLabel = computed(() => formatValue(maxValue.value));

const legendGradient = computed(
  () => `linear-gradient(90deg, ${colorFor(minValue.value)} 0%, ${colorFor(maxValue.value)} 100%)`
);

const gridStyle = computed(() => ({
  gridTemplateColumns: `180px repeat(${props.quarters.length}, 96px)`
}));

function getCell(country, quarter) {
  return cellMap.value[`${country}__${quarter}`] || null;
}

function colorFor(value) {
  if (!Number.isFinite(value)) {
    return "rgba(242, 230, 211, 0.62)";
  }

  const min = minValue.value;
  const max = maxValue.value;
  const ratio = max > min ? (value - min) / (max - min) : 0.5;

  const start = { r: 232, g: 240, b: 234 };
  const end = { r: 29, g: 107, b: 87 };
  const mix = (left, right) => Math.round(left + (right - left) * ratio);

  return `rgb(${mix(start.r, end.r)} ${mix(start.g, end.g)} ${mix(start.b, end.b)})`;
}

function formatValue(value) {
  return props.valueFormatter(value);
}

function ariaLabel(country, quarter) {
  const cell = getCell(country, quarter);
  return cell ? `${country} ${quarter} ${formatValue(cell.value)}` : `${country} ${quarter} no data`;
}
</script>

<style scoped>
.quarter-heatmap {
  display: grid;
  gap: 0.8rem;
}

.heatmap-wrap {
  width: max-content;
  max-width: 100%;
}

.heatmap-active {
  padding: 0.75rem 0.9rem;
  border-radius: 14px;
  background: rgba(242, 230, 211, 0.42);
  border: 1px solid rgba(31, 42, 31, 0.08);
}

.heatmap-active p {
  margin: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 0.7rem;
  color: var(--muted);
}

.heatmap-active strong {
  color: var(--ink);
}

.heat-cell {
  padding: 0;
  width: 96px;
  height: 72px;
  aspect-ratio: auto;
  border-radius: 0;
}

.heat-cell:focus-visible {
  outline: 2px solid rgba(31, 42, 31, 0.45);
  outline-offset: 2px;
}

@media (max-width: 1100px) {
  .heat-cell {
    width: 82px;
    height: 62px;
  }
}
</style>
