<template>
  <ChartSlot title="Global COVID and Vaccination Trend" description="Connect this to exported HTML from pyecharts/plotly or backend API data.">
    <PythonVizFrame src="" />
  </ChartSlot>
</template>

<script setup>
import ChartSlot from "../../components/ChartSlot.vue";
import PythonVizFrame from "../../components/PythonVizFrame.vue";
</script>
