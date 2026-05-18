<template>
  <div ref="chartRef" class="plotly-host" :style="hostStyle"></div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import Plotly from "plotly.js-dist-min";

const props = defineProps({
  figure: {
    type: Object,
    default: null
  },
  height: {
    type: Number,
    default: 520
  }
});

const chartRef = ref(null);

const hostStyle = computed(() => ({
  height: `${props.height}px`
}));

function cloneFigurePart(value) {
  if (value === null || value === undefined) {
    return value;
  }

  if (typeof structuredClone === "function") {
    return structuredClone(value);
  }

  return JSON.parse(JSON.stringify(value));
}

async function renderChart() {
  if (!chartRef.value || !props.figure) {
    return;
  }

  const { data = [], layout = {}, config = {}, frames = [] } = props.figure;
  const plotData = cloneFigurePart(data) || [];
  const plotLayout = cloneFigurePart(layout) || {};
  const plotConfig = cloneFigurePart(config) || {};
  const plotFrames = cloneFigurePart(frames) || [];

  await nextTick();
  if (chartRef.value.data) {
    await Plotly.react(chartRef.value, plotData, plotLayout, {
      responsive: true,
      displayModeBar: false,
      ...plotConfig
    });
  } else {
    await Plotly.newPlot(chartRef.value, plotData, plotLayout, {
      responsive: true,
      displayModeBar: false,
      ...plotConfig
    });
  }

  if (plotFrames.length) {
    await Plotly.deleteFrames(chartRef.value);
    await Plotly.addFrames(chartRef.value, plotFrames);
  }
}

onMounted(renderChart);

watch(
  () => [props.figure, props.height],
  () => {
    renderChart();
  }
);

onBeforeUnmount(() => {
  if (chartRef.value) {
    Plotly.purge(chartRef.value);
  }
});
</script>

<style scoped>
.plotly-host {
  width: 100%;
}
</style>
