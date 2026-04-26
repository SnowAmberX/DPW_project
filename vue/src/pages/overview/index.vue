<template>
  <section class="panel-card">
    <p class="eyebrow">Overview</p>
    <h1 class="hero-title">COVID-19 Situation and Vaccination Overview</h1>
    <p class="section-note">
      Dashboard landing page that mirrors Streamlit's overview entry and keeps the same analytical context.
    </p>
  </section>
  <div class="page-grid">
    <OverviewCharts />
  </div>
</template>

<script setup>
import OverviewCharts from "./OverviewCharts.vue";
</script>
