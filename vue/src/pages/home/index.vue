<template>
  <section class="hero-layout">
    <div class="panel-card">
      <h1 class="hero-title">Home</h1>
      <p class="section-note">COVID-19 Vaccine Impact Analysis Platform</p>
      <p class="section-note">
        A refactored analytical dashboard focused on vaccine rollout context, mortality signals, and future prediction
        workflows. The map remains available as supporting context rather than the primary analysis surface.
      </p>
    </div>
    <!-- <div class="hero-image-card">
      <img class="hero-image" src="/illustrations/home-overview.svg" alt="Home illustration" />
    </div> -->
  </section>
  <div class="page-grid">
    <HomeCharts />
  </div>
</template>

<script setup>
import HomeCharts from "./HomeCharts.vue";
</script>
