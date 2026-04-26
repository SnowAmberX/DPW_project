<template>
  <ChartSlot title="Future Outbreak Forecast" description="输入 seed-country 后调用 neural API，按日期展示各国预测新增病例。">
    <NeuralPredictionTimeline />
  </ChartSlot>
</template>

<script setup>
import ChartSlot from "../../components/ChartSlot.vue";
import NeuralPredictionTimeline from "../../components/NeuralPredictionTimeline.vue";
</script>
