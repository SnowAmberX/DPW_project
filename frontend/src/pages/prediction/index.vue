<template>
  <section class="panel-card">
    <p class="eyebrow">Prediction</p>
    <h1 class="hero-title">Future Outbreak Prediction</h1>
    <p class="section-note">
      This page aligns with the Streamlit prediction section and keeps a reserved area for model-based forecast visuals.
    </p>
  </section>
  <div class="page-grid">
    <PredictionCharts />
  </div>
</template>

<script setup>
import PredictionCharts from "./PredictionCharts.vue";
</script>
