<template>
  <section class="panel-card mortality-hero">
    <h1 class="hero-title">Vaccination status and mortality</h1>
    <p class="section-note mortality-sub">
      This interactive dashboard examines how COVID-19 vaccination coverage and mortality patterns changed across countries
      during the pandemic. The visualizations highlight broad trends such as declining mortality following large-scale vaccination
      rollout, differences between regions, and the higher vulnerability of older populations. The project focuses on
      comparative patterns and statistical relationships rather than causal conclusions.
    </p>
  </section>

  <div class="page-grid mortality-grid">
    <MortalityVaccinationCharts />
  </div>
</template>

<script setup>
import MortalityVaccinationCharts from "./MortalityVaccinationCharts.vue";
</script>

<style scoped>
.mortality-sub {
  margin: 0.55rem 0 0;
  width: 100%;
  max-width: none;
  line-height: 1.58;
  text-align: justify;
  text-wrap: pretty;
}

.mortality-grid {
  grid-template-columns: 1fr;
}
</style>
