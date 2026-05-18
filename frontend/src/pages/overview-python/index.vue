<template>
  <div class="overview-python-page">
    <section class="panel-card overview-hero">
      <p class="eyebrow">Vaccination status</p>
      <h1 class="hero-title">Vaccination Status Overview</h1>
      <p class="section-note overview-subtitle">
        This dashboard summarizes quarterly COVID-19 vaccination rollout patterns across regions and income groups from
        2020 through the end of 2023. The views focus on rollout timing, coverage progress, and broad differences between
        group-level vaccination trajectories.
      </p>
    </section>

    <section class="panel-card overview-section">
      <article class="viz-card viz-card-wide">
        <div class="viz-toolbar">
          <div>
            <p class="viz-kicker">Animated view</p>
            <h4>Vaccination Rollout Paths Across Groups</h4>
          </div>
        </div>
        <p class="viz-chart-intro">
          This chart compares quarterly vaccination rollout trajectories across representative regions and income groups from
          2020 through the end of 2023. Each line tracks one group over time, while the animation builds the trajectories
          quarter by quarter.
        </p>
        <p class="viz-chart-intro">
          Rollout speed was concentrated in earlier pandemic stages for several higher-coverage groups, while completion
          measures changed more gradually as countries moved from initial uptake toward full vaccination.
        </p>
        <p class="viz-chart-intro">
          The line patterns therefore suggest a heterogeneous global rollout process, with timing and intensity varying
          substantially across regions and income bands rather than following one uniform path.
        </p>
        <PythonVizFrame src="/python-viz/overview-rollout-paths.html" :height="638" />
      </article>

      <article class="viz-card viz-card-wide">
        <div class="viz-toolbar">
          <div>
            <p class="viz-kicker">Overview 3</p>
            <h4>Cross-group Quarterly Vaccination Matrix</h4>
          </div>
        </div>
        <p class="viz-chart-intro">
          This matrix compares quarterly vaccination progress across world regions and income groups. Quarters run across
          the x-axis, groups run down the y-axis, and darker cells indicate higher values for the selected vaccination
          metric.
        </p>
        <p class="viz-chart-intro">
          The matrix highlights that vaccination expansion did not occur at the same pace everywhere. Higher-income and
          European groups generally show earlier and stronger coverage signals, while lower-income groups remain lighter
          for longer periods.
        </p>
        <p class="viz-chart-intro">
          The view should be read as a descriptive comparison of rollout timing rather than a complete explanation of
          country-level access, policy, or reporting differences.
        </p>
        <PythonVizFrame src="/python-viz/overview-group-matrix.html" :height="628" />
      </article>

      <article class="viz-card viz-card-wide">
        <div class="viz-toolbar">
          <div>
            <p class="viz-kicker">Global lens</p>
            <h4>Quarterly vaccination and case situation</h4>
          </div>
        </div>
        <p class="viz-chart-intro">
          These cards summarize the selected quarter by highlighting the strongest visible vaccination, case, and
          group-level signals. They provide a quick reference for the current frame before reading the detailed
          matrix and fitted rollout summary.
        </p>
        <PythonVizFrame src="/python-viz/overview-quarter-summary.html" :height="788" />
      </article>
    </section>

    <section class="panel-card section-card curve-summary-section">
      <div class="section-heading summary-heading">
        <div>
          <p class="viz-kicker">Curve fit analysis</p>
          <h2>Statistical Summary of Curve Fitting</h2>
        </div>
      </div>

      <article class="viz-card viz-card-wide">
        <div class="viz-toolbar">
          <div>
            <p class="viz-kicker">Main fitted view</p>
            <h4>Observed vs fitted rollout trajectories</h4>
          </div>
        </div>
        <p class="model-note">
          Representative groups are shown as compact multiples. Solid lines are fitted values, dots are observed values,
          red markers indicate the steepest fitted growth quarter, and green markers or guides mark fitted transition points.
          Hover over the markers for the exact quarter and value.
        </p>
        <PythonVizFrame src="/python-viz/overview-curve-fit.html" :height="768" />
      </article>

      <article class="viz-card viz-card-wide">
        <div class="viz-toolbar">
          <div>
            <p class="viz-kicker">Modeling summary</p>
            <h4>Curve-fit Summary Panel</h4>
          </div>
        </div>
        <p class="model-note">
          First-dose and full-vaccination trajectories are fitted across group-level rollout curves. These counts summarize
          model choice only; parameter values are interpreted conservatively within each model family.
        </p>
        <PythonVizFrame src="/python-viz/overview-curve-summary.html" :height="568" />
      </article>
    </section>
  </div>
</template>

<script setup>
import PythonVizFrame from "../../components/PythonVizFrame.vue";
</script>

<style scoped>
.overview-python-page,
.overview-section,
.curve-summary-section {
  display: grid;
  gap: 1rem;
  min-width: 0;
}

.overview-python-page > .panel-card,
.overview-python-page > .overview-section {
  animation: fade-up 0.45s ease both;
}

.overview-hero {
  display: grid;
  gap: 0.35rem;
}

.overview-subtitle {
  margin: 0.25rem 0 0;
  max-width: 1080px;
  line-height: 1.62;
}

.overview-section,
.curve-summary-section {
  padding: 0.85rem 1rem 1rem;
}

.viz-card {
  padding: 0.72rem 0.95rem 0.28rem;
}

.viz-toolbar {
  margin-bottom: 0.45rem;
}

.viz-chart-intro,
.model-note {
  margin: 0 0 0.42rem;
  width: 100%;
  max-width: none;
  color: var(--muted, #5e6b60);
  font-size: 1.045rem;
  line-height: 1.55;
  text-align: justify;
  text-wrap: pretty;
}

.summary-heading {
  align-items: flex-start;
}

:deep(.python-viz-frame-root) {
  margin-bottom: 0;
}

:deep(.viz-card) {
  min-width: 0;
  overflow: hidden;
  border-radius: 10px;
}

@keyframes fade-up {
  from {
    opacity: 0;
    transform: translateY(8px);
  }

  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
