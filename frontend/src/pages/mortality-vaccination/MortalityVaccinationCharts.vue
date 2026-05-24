<template>
  <section class="panel-card mortality-charts-shell">
    <div class="analysis-stack">
      <section class="viz-card">
        <div class="viz-toolbar">
          <div>
            <p class="viz-kicker">Timeline</p>
            <h4>National rollout and mortality dynamics</h4>
          </div>
        </div>
        <p class="viz-chart-intro">
          This chart compares COVID-19 vaccination coverage and mortality trends across countries from 2020 through the end of
          2023.
        </p>
        <p class="viz-chart-intro">
          Mortality fluctuated heavily during earlier pandemic stages, while many regions later experienced lower and more stable
          mortality patterns alongside increasing vaccination coverage.
        </p>
        <p class="viz-chart-intro">
          However, mortality decline did not occur uniformly across countries, and fluctuations still appeared during later
          pandemic stages. The timeline therefore suggests a dynamic and heterogeneous mortality response during the vaccination
          period rather than a single consistent pattern.
        </p>
        <PythonVizFrame src="/mortality-vaccination/timeline-country.html" :height="568" />
      </section>

      <section class="viz-card">
        <div class="viz-toolbar">
          <div>
            <p class="viz-kicker">Scatter</p>
            <h4>Vaccination coverage vs daily mortality</h4>
          </div>
        </div>
        <p class="viz-chart-intro">
          This animated scatter plot tracks how vaccination coverage and COVID-19 mortality changed across countries over time. Each
          bubble represents a country.
        </p>
        <p class="viz-chart-intro">
          As vaccination coverage increased, many countries gradually shifted toward lower mortality regions over time.
        </p>
        <p class="viz-chart-intro">
          However, countries still followed different mortality trajectories, and similar vaccination levels did not always
          correspond to similar mortality outcomes. Several countries also experienced temporary mortality increases even after
          achieving relatively high vaccination coverage.
        </p>
        <p class="viz-chart-intro">
          The visualization highlights that mortality response remained heterogeneous across countries during the pandemic.
        </p>
        <PythonVizFrame src="/mortality-vaccination/scatter-correlation.html" :height="658" />
      </section>

      <section class="viz-card">
        <div class="viz-toolbar">
          <div>
            <p class="viz-kicker">Heatmap</p>
            <h4>Cross-country Pandemic Patterns</h4>
          </div>
        </div>
        <p class="viz-chart-intro">
          This heatmap compares quarterly pandemic patterns across countries and regions using three indicators: mortality,
          vaccination coverage, and infection pressure. Darker cells indicate higher levels within each metric. Switching between
          views reveals how vaccination expanded over time, how mortality changed across regions, and how infection waves varied
          between countries. The matrix highlights that pandemic experiences were not synchronized globally, with different
          countries reaching peak pressure and recovery periods at different times.
        </p>
        <ul class="viz-bullets">
          <li>Vaccination coverage increased steadily across most countries after 2021.</li>
          <li>
            Mortality peaks were concentrated in earlier pandemic stages and generally became less severe over time.
          </li>
          <li>
            Pandemic timing and outbreak patterns varied substantially across countries and regions.
          </li>
        </ul>
        <PythonVizFrame src="/mortality-vaccination/heatmap-matrix.html" :height="628" />
      </section>

      <section class="viz-card">
        <div class="viz-toolbar">
          <div>
            <p class="viz-kicker">Threshold ranking</p>
            <h4>Mortality change around vaccination thresholds</h4>
          </div>
        </div>
        <p class="viz-chart-intro">
          For each entity we take the first calendar month where vaccinated_pct reaches the chosen threshold (30%, 50%, or 70%).
          Before is the mean daily deaths per 100k in the three months immediately preceding that month; after is the mean in
          that threshold month plus the following two months (three months total). The right panel plots change = before minus
          after: positive values (green markers) mean mortality fell across the windows; negative (amber) mean it rose. Different
          thresholds fall at different time periods across countries, so the before/after windows vary over time and mortality
          changes do not follow a single uniform pattern.
        </p>
        <PythonVizFrame src="/mortality-vaccination/ranking-threshold.html" :height="568" />
      </section>

      <section class="viz-card">
        <div class="viz-toolbar">
          <div>
            <p class="viz-kicker">Age bands</p>
            <h4>Age-group Vaccination and Vulnerability</h4>
          </div>
        </div>
        <p class="viz-chart-intro">
          This chart compares vaccination coverage across age groups while providing an illustrative age-related vulnerability
          context.
        </p>
        <p class="viz-chart-intro">
          The bars show the share of people receiving at least one dose, full vaccination, and booster doses.
        </p>
        <p class="viz-chart-intro">
          Vulnerability markers reflect broadly observed age-related differences in severe COVID-19 outcomes and are intended for
          comparative visualization rather than precise clinical risk estimation.
        </p>
        <p class="viz-chart-intro">
          The chart highlights that older populations remained relatively more vulnerable even under high vaccination coverage.
        </p>
        <PythonVizFrame src="/mortality-vaccination/age-risk-context.html" :height="688" />
      </section>

      <section class="viz-card">
        <div class="viz-toolbar">
          <div>
            <p class="viz-kicker">Quantitative summary</p>
            <h4>Statistical Summary</h4>
          </div>
        </div>
        <p class="viz-chart-intro">
          These tables summarize statistical patterns in vaccination coverage, outbreak intensity, and COVID-19 mortality across
          selected countries and regions.
        </p>
        <p class="viz-chart-intro">
          The results suggest that mortality patterns remained influenced by multiple factors during the pandemic.
        </p>
        <p class="viz-chart-intro">
          While vaccination coverage showed a weak negative relationship with mortality, cases per 100k population demonstrated a
          substantially stronger positive association with mortality fluctuations.
        </p>
        <p class="viz-chart-intro">
          All relationships shown here are observational and should be interpreted as descriptive rather than causal.
        </p>
        <ul class="viz-bullets">
          <li>
            Vaccination coverage showed only a weak negative association with mortality across the pooled observations.
          </li>
          <li>Cases per 100k population remained more strongly associated with mortality fluctuations.</li>
          <li>
            Statistical relationships varied across countries and periods, reflecting heterogeneous pandemic conditions.
          </li>
        </ul>
        <PythonVizFrame
          src="/mortality-vaccination/mortality-stats-tables.html"
          :height="628"
          :no-scroll="true"
        />
      </section>
    </div>
  </section>
</template>

<script setup>
import PythonVizFrame from "../../components/PythonVizFrame.vue";
</script>

<style scoped>
.mortality-charts-shell {
  padding: 0.85rem 1rem 1rem;
}

.mortality-charts-shell .analysis-stack {
  gap: 0.55rem;
}

.mortality-charts-shell :deep(.viz-toolbar) {
  margin-bottom: 0.45rem;
}

.mortality-charts-shell :deep(.viz-card) {
  padding: 0.72rem 0.95rem 0.28rem;
}

.viz-chart-intro {
  margin: 0 0 0.42rem;
  width: 100%;
  max-width: none;
  color: var(--muted, #5e6b60);
  font-size: 1.045rem;
  line-height: 1.55;
  text-align: justify;
  text-wrap: pretty;
}

.viz-bullets {
  margin: 0 0 0.42rem;
  padding-left: 1.05rem;
  color: var(--muted, #5e6b60);
  font-size: 1.01rem;
  line-height: 1.5;
}

.viz-bullets li + li {
  margin-top: 0.2rem;
}

.viz-note {
  margin: 0 0 0.42rem;
  color: var(--muted, #5e6b60);
  font-size: 1.01rem;
  line-height: 1.5;
}

.viz-chart-footnote {
  margin: 0.65rem 0 0;
  font-size: 0.98rem;
}

.mortality-charts-shell :deep(.python-viz-frame-root) {
  margin-bottom: 0;
}
</style>
