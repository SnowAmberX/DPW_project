<template>
  <section class="hero-layout">
    <div class="panel-card home-hero-copy">
      <p class="eyebrow">Vaccine Impact Lab</p>
      <h1 class="hero-title">Vaccine Impact Analysis Lab</h1>
      <p class="section-note home-lead">
        An analytical workspace for vaccination rollout, mortality context, case dynamics, and forward-looking scenarios —
        tied together with reproducible data prep and interactive charts so you read rollout, health outcomes, and
        projections as one story instead of disconnected dashboards.
      </p>
    </div>
    <div class="hero-image-card">
      <img
        class="hero-image"
        src="/illustrations/home-hero-vaccination.png"
        alt="Vaccination and virus illustration"
      />
    </div>
  </section>

  <section class="panel-card home-intro-block">
    <h2 class="home-section-title">Start here</h2>
    <p class="section-note">
      The cards below mirror the top navigation. Begin with the vaccination status overview for cross-country alignment,
      quarterly heatmaps, and age-stratified views.
    </p>
  </section>

  <div class="page-grid">
    <HomeCharts />
  </div>
</template>

<script setup>
import HomeCharts from "./HomeCharts.vue";
</script>

<style scoped>
.hero-layout {
  grid-template-columns: 0.85fr 1.15fr;
  gap: 0.3rem;
}

.home-hero-copy {
  max-width: 520px;
}

.home-lead {
  margin-top: 0.65rem;
  max-width: 34rem;
  line-height: 1.65;
}

.hero-image-card {
  overflow: hidden;
  border-radius: 20px;
  border: 1px solid var(--border);
  background: rgba(255, 250, 242, 0.88);
  box-shadow: 0 16px 40px rgba(61, 48, 29, 0.08);
  backdrop-filter: blur(8px);
  min-height: 450px;
  display: grid;
  place-items: center;
  padding: 0.45rem;
}

.hero-image {
  height: 100%;
  width: 100%;
  object-fit: cover;
  object-position: 34% center;
  display: block;
}

.home-intro-block {
  margin-top: 1rem;
}

.home-section-title {
  margin: 0 0 0.5rem;
  font-size: 1.2rem;
  font-weight: 700;
  color: var(--ink, #1f2a1f);
}

@media (max-width: 960px) {
  .hero-layout {
    grid-template-columns: 1fr;
  }

  .home-hero-copy {
    max-width: none;
  }

  .hero-image-card {
    min-height: 320px;
    padding: 0.65rem;
  }

  .hero-image {
    height: 320px;
  }
}
</style>
