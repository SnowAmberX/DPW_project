<template>
  <section class="panel-card rollout-hero">
    <p class="eyebrow">Vaccination rollout</p>
    <h1 class="hero-title">Vaccination Rollout Analysis</h1>
    <p class="section-note rollout-subtitle">
      Compare early rollout speed, completion patterns, and age-priority strategies across selected countries using
      interactive views derived from cleaned vaccination datasets.
    </p>
  </section>

  <VaccinationRolloutCharts />
</template>

<script setup>
import VaccinationRolloutCharts from "./VaccinationRolloutCharts.vue";
</script>

<style scoped>
.rollout-hero {
  display: grid;
  gap: 0.35rem;
}

.rollout-subtitle {
  margin: 0.25rem 0 0;
  max-width: 980px;
  line-height: 1.62;
}
</style>
