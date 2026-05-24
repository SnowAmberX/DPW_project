<template>
  <RouterLink v-for="card in cards" :key="card.to" :to="card.to" class="home-feature-card">
    <span class="home-feature-kicker">{{ card.kicker }}</span>
    <h3 class="home-feature-title">{{ card.title }}</h3>
    <p class="home-feature-desc">{{ card.desc }}</p>
    <span class="home-feature-cta">Explore →</span>
  </RouterLink>
</template>

<script setup>
import { RouterLink } from "vue-router";

const cards = [
  {
    to: "/overview",
    kicker: "Status",
    title: "Vaccination Status Overview",
    desc: "Aligned rollout timelines, quarterly intensity, age-priority views, and narrative findings — the first stop to compare global pacing in one place."
  },
  {
    to: "/cases-vaccination",
    kicker: "Cases",
    title: "Vaccination vs new cases",
    desc: "Country curves, lagged correlations, and before/after peak views to relate programme scale-up to epidemic waves."
  },
  {
    to: "/mortality-vaccination",
    kicker: "Mortality",
    title: "Vaccination vs mortality",
    desc: "Dual-axis timelines, animated scatter, quarterly matrices, and threshold groupings to see how burden shifts as coverage rises."
  },
  {
    to: "/prediction",
    kicker: "Forecast",
    title: "Future outbreak scenarios",
    desc: "Explore forward-looking timelines in the same interactive frame and read projections next to historical context."
  }
];
</script>

<style scoped>
.home-feature-card {
  display: grid;
  gap: 0.45rem;
  align-content: start;
  padding: 1.15rem 1.2rem;
  text-decoration: none;
  color: inherit;
  background: rgba(255, 250, 242, 0.92);
  border: 1px solid rgba(31, 42, 31, 0.08);
  border-radius: 18px;
  box-shadow: 0 12px 32px rgba(61, 48, 29, 0.06);
  transition:
    transform 0.18s ease,
    box-shadow 0.18s ease,
    border-color 0.18s ease;
}

.home-feature-card:hover {
  transform: translateY(-3px);
  border-color: rgba(29, 107, 87, 0.25);
  box-shadow: 0 18px 44px rgba(29, 67, 56, 0.12);
}

.home-feature-kicker {
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--accent-2, #b85c38);
}

.home-feature-title {
  margin: 0;
  font-size: 1.12rem;
  line-height: 1.35;
  color: var(--ink, #1f2a1f);
}

.home-feature-desc {
  margin: 0;
  color: var(--muted, #5e6b60);
  font-size: 0.98rem;
  line-height: 1.55;
}

.home-feature-cta {
  margin-top: 0.35rem;
  font-size: 0.92rem;
  font-weight: 600;
  color: var(--accent, #1d6b57);
}
</style>
