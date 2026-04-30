<template>
  <ChartSlot
    title="Future Outbreak Forecast"
    description="Click a seed country to call the selected model and render forecast frames by date."
  >
    <NeuralPredictionTimeline />
  </ChartSlot>
</template>

<script setup>
import ChartSlot from "../../components/ChartSlot.vue";
import NeuralPredictionTimeline from "../../components/NeuralPredictionTimeline.vue";
</script>
