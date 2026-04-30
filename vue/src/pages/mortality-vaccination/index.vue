<template>
  <section class="panel-card">
    <h1 class="hero-title">Vaccination Status and Mortality Rate</h1>
    <p class="section-note">
      Focus this page on mortality-oriented indicators, comparative time trends, and turning-point style interpretation.
    </p>
  </section>
  <section class="panel-card page-image-block">
    <img class="page-image" src="/illustrations/mortality-vaccination.svg" alt="Vaccination and mortality illustration" />
  </section>
  <div class="page-grid">
    <MortalityVaccinationCharts />
  </div>
</template>

<script setup>
import MortalityVaccinationCharts from "./MortalityVaccinationCharts.vue";
</script>
