<template>
  <ChartSlot title="Vaccination Rate vs New Cases" description="Recommended: scatter plot, lagged-correlation plot, or dual-axis time series.">
    <PythonVizFrame src="" />
  </ChartSlot>
</template>

<script setup>
import ChartSlot from "../../components/ChartSlot.vue";
import PythonVizFrame from "../../components/PythonVizFrame.vue";
</script>
