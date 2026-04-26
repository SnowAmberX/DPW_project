<template>
  <ChartSlot title="Vaccination Rate vs Mortality Rate" description="Recommended: age-segment mortality trends and vaccination-group comparison charts.">
    <PythonVizFrame src="" />
  </ChartSlot>
</template>

<script setup>
import ChartSlot from "../../components/ChartSlot.vue";
import PythonVizFrame from "../../components/PythonVizFrame.vue";
</script>
