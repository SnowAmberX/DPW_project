<template>
  <section class="panel-card">
    <h1 class="hero-title">Vaccination Status and New Cases</h1>
    <p class="section-note">
      Compare vaccine uptake across countries, inspect milestone timing, and surface short narrative summaries from
      the selected time window.
    </p>
    <p class="section-note">
      Focus this page on explanatory relationships between rollout indicators and downstream outcome signals.
    </p>
  </section>
  <!-- <section class="panel-card page-image-block">
    <img class="page-image" src="/illustrations/cases-vaccination.svg" alt="Vaccination and new cases illustration" />
  </section> -->
  <div class="page-grid">
    <CasesVaccinationCharts />
  </div>
</template>

<script setup>
import CasesVaccinationCharts from "./CasesVaccinationCharts.vue";
</script>
