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
        src="/home/home-hero-vaccination.png"
        alt="Vaccination and virus illustration"
      />
    </div>
  </section>

  <section class="panel-card why-section">
    <div class="why-copy">
      <p class="eyebrow">Why we do this</p>
      <h2 class="home-section-title">Turning vaccine data into readable public-health evidence</h2>
      <p class="section-note why-lead">
        Vaccination data is useful only when it can be read alongside outbreaks, mortality burden, and time. This project
        brings those views together so differences in rollout speed, coverage, and health outcomes can be compared in one
        consistent analytical frame.
      </p>
    </div>
    <div class="why-points" aria-label="Project motivation">
      <div class="why-point">
        <span class="why-point-kicker">Compare</span>
        <p>Track how rollout timing differs across countries, regions, and income groups.</p>
      </div>
      <div class="why-point">
        <span class="why-point-kicker">Connect</span>
        <p>Read vaccination progress next to case waves and mortality patterns instead of isolated charts.</p>
      </div>
      <div class="why-point">
        <span class="why-point-kicker">Anticipate</span>
        <p>Use historical signals to frame forward-looking outbreak scenarios with clearer context.</p>
      </div>
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

.why-section {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(360px, 0.95fr);
  gap: 1.15rem;
  align-items: start;
  margin-top: 1rem;
}

.why-copy {
  max-width: 680px;
}

.home-section-title {
  margin: 0 0 0.5rem;
  font-size: 1.2rem;
  font-weight: 700;
  color: var(--ink, #1f2a1f);
}

.why-lead {
  line-height: 1.58;
}

.why-points {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.75rem;
}

.why-point {
  min-height: 132px;
  padding: 0.9rem;
  border: 1px solid rgba(31, 42, 31, 0.08);
  border-radius: 14px;
  background: rgba(242, 230, 211, 0.36);
}

.why-point-kicker {
  display: block;
  margin-bottom: 0.5rem;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--accent, #1d6b57);
}

.why-point p {
  margin: 0;
  color: var(--muted, #5e6b60);
  font-size: 0.96rem;
  line-height: 1.48;
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

  .why-section,
  .why-points {
    grid-template-columns: 1fr;
  }

  .why-point {
    min-height: 0;
  }
}
</style>
