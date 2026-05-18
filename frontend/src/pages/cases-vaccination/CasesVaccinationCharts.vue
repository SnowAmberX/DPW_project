<template>
  <section class="analysis-section">
    <section class="analysis-hero">
      <div class="hero-copy">
        <p class="eyebrow">Python-based analysis - 2020-2023</p>
        <h2>Vaccination Rate vs New Cases</h2>
        <p>
          This page compares COVID-19 vaccination coverage and new-case patterns across the United States, China, India,
          and Japan from 2020 through the end of 2023.
        </p>
        <p>
          The visualizations place vaccination progress alongside case pressure so that broad timing relationships can be
          inspected before moving into lagged and cross-country comparisons.
        </p>
        <p>
          Case waves did not decline uniformly as vaccination coverage increased. The page therefore presents the
          vaccination-case relationship as dynamic and heterogeneous rather than as a single direct response pattern.
        </p>
      </div>

      <div class="hero-stats">
        <article>
          <span>4</span>
          <p>Countries</p>
        </article>
        <article>
          <span>2020-2023</span>
          <p>Time range</p>
        </article>
        <article>
          <span>28-day</span>
          <p>Lag test</p>
        </article>
      </div>
    </section>

    <section class="interactive-module">
      <div class="module-header compact-header">
        <div>
          <p class="eyebrow">Opening interactive overview</p>
          <h3>Interactive Overview: Vaccination Coverage vs New Cases</h3>
          <p>
            This animated overview tracks how each country moves through vaccination coverage and new-case pressure over
            time. Each bubble represents one country-month, with movement showing how coverage and case burden changed
            across the pandemic period.
          </p>
          <p>
            Vaccination coverage generally increased over time, but case pressure continued to appear in waves. This
            makes the animation useful for seeing broad movement without assuming that higher coverage immediately
            produced a uniform decline in cases.
          </p>
        </div>
      </div>

      <div class="animated-chart">
        <AnimatedCaseBubbleChart />
      </div>

      <p class="overview-note">
        The animated view highlights that vaccination coverage and case pressure moved on different timelines across the
        four countries. It provides a descriptive overview of changing pandemic conditions rather than evidence of a
        single causal pathway.
      </p>
    </section>

    <section class="main-module">
      <div class="module-header">
        <div>
          <p class="eyebrow">Analysis board</p>
          <h3>{{ activeChart.title }}</h3>
          <p>{{ activeChart.description }}</p>
        </div>

        <div class="module-tabs">
          <button
            v-for="chart in charts"
            :key="chart.key"
            type="button"
            :class="{ active: activeKey === chart.key }"
            @click="activeKey = chart.key"
          >
            {{ chart.shortTitle }}
          </button>
        </div>
      </div>

      <div class="chart-display">
        <div class="chart-topbar">
          <div>
            <p class="chart-number">{{ activeChart.number }}</p>
            <strong>{{ activeChart.badge }}</strong>
          </div>
          <span>{{ activeChart.period }}</span>
        </div>

        <iframe
          class="chart-frame"
          :class="activeChart.frameClass"
          :src="activeChart.src"
          :title="activeChart.titleAttr"
          loading="lazy"
        ></iframe>
      </div>

      <div class="analysis-note">
        <p>{{ activeChart.explain }}</p>
        <p class="analysis-conclusion">{{ activeChart.conclusion }}</p>
      </div>
    </section>
  </section>
</template>

<script setup>
import { computed, ref } from "vue";
import AnimatedCaseBubbleChart from "../../components/AnimatedCaseBubbleChart.vue";

const activeKey = ref("trend");

const charts = [
  {
    key: "trend",
    number: "Analysis 1",
    shortTitle: "Trend",
    badge: "Vaccination rate and new cases over time",
    title: "Trend Analysis: Vaccination Rate and New Cases",
    description: "This timeline compares vaccination coverage and new-case waves across the four countries.",
    explain:
      "This chart compares vaccination rollout and new-case trends over time. It places coverage progress and case waves on the same timeline so that broad timing differences can be inspected across countries.",
    conclusion:
      "Vaccination coverage rises quickly during the main rollout period, but case waves still appear at different times. The timeline therefore suggests a heterogeneous case response rather than a single consistent decline after vaccination.",
    period: "2020-2023",
    src: "/analysis/cases-vaccination/01_trend_vaccination_vs_cases.html",
    titleAttr: "Vaccination rate vs new cases trend",
    frameClass: "frame-tall",
  },
  {
    key: "correlation",
    number: "Analysis 2",
    shortTitle: "Correlation",
    badge: "28-day lag relationship",
    title: "Correlation Analysis with 28-day Lag",
    description: "This view compares vaccination coverage with new-case pressure 28 days later.",
    explain:
      "This scatter plot examines whether higher vaccination coverage is associated with later new-case levels after a 28-day lag. The log-scaled y-axis keeps both low- and high-case observations visible.",
    conclusion:
      "The points remain widely dispersed, so the lag relationship should not be read as a simple straight-line effect. The chart instead suggests that vaccination coverage is only one part of a broader and variable case pattern.",
    period: "28-day lag",
    src: "/analysis/cases-vaccination/03_correlation_scatter_28day_lag.html",
    titleAttr: "Correlation between vaccination rate and new cases",
    frameClass: "frame-tall",
  },
  {
    key: "countries",
    number: "Analysis 3",
    shortTitle: "Countries",
    badge: "Case waves and vaccination milestones",
    title: "Cross-country Comparison",
    description: "This view compares case waves and vaccination milestone timing across the four countries.",
    explain:
      "This chart compares how vaccination milestones and case waves appeared across countries. It highlights when each country reached key coverage points and how those milestones aligned with later case pressure.",
    conclusion:
      "The four countries do not follow one identical timeline. Rollout speed, wave timing, and later case pressure differ, which supports a country-by-country interpretation rather than a single universal pattern.",
    period: "Cases + milestones",
    src: "/analysis/cases-vaccination/04_cross_country_comparison.html",
    titleAttr: "Cross-country comparison",
    frameClass: "frame-medium",
  },
  {
    key: "peaks",
    number: "Analysis 4",
    shortTitle: "Peaks",
    badge: "Before vs after broad vaccination",
    title: "Peak Analysis before and after Vaccination Rollout",
    description: "This supporting view compares peak case pressure before and after broad vaccination rollout.",
    explain:
      "This chart compares the highest new-case peaks in lower- and higher-vaccination periods. It provides a compact before-and-after style summary for each country.",
    conclusion:
      "Peak changes are not identical across countries, so this view is best used as supporting evidence. Differences in variants, testing intensity, public policy, and reporting context may still shape the observed case peaks.",
    period: "Peak comparison",
    src: "/analysis/cases-vaccination/05_peak_before_after_rollout.html",
    titleAttr: "Peak analysis before and after vaccination rollout",
    frameClass: "frame-short",
  },
];

const activeChart = computed(() => charts.find((chart) => chart.key === activeKey.value) || charts[0]);
</script>

<style scoped>
.analysis-section {
  display: flex;
  flex-direction: column;
  gap: 28px;
}

.analysis-hero {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) minmax(280px, 0.75fr);
  gap: 24px;
  padding: 32px;
  border-radius: 30px;
  background: #f7f4ee;
  border: 1px solid rgba(207, 198, 183, 0.86);
  box-shadow: 0 16px 38px rgba(35, 54, 47, 0.08);
}

.eyebrow,
.chart-number,
.side-label {
  margin: 0 0 8px;
  color: #c06a42;
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 0.09em;
  text-transform: uppercase;
}

.hero-copy h2 {
  margin: 0 0 14px;
  color: #23362f;
  font-size: 38px;
  line-height: 1.1;
}

.hero-copy p,
.module-header p,
.analysis-note p {
  margin: 0;
  color: #627168;
  line-height: 1.65;
  font-size: 15px;
}

.hero-stats {
  display: grid;
  gap: 12px;
}

.hero-stats article {
  padding: 18px 20px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.62);
  border: 1px solid rgba(188, 174, 154, 0.78);
}

.hero-stats span {
  display: block;
  margin-bottom: 4px;
  color: #23362f;
  font-size: 25px;
  font-weight: 850;
}

.hero-stats p {
  margin: 0;
  color: #627168;
  font-size: 13px;
}

.main-module,
.interactive-module {
  padding: 28px;
  border-radius: 30px;
  background: #f7f4ee;
  border: 1px solid rgba(207, 198, 183, 0.86);
  box-shadow: 0 16px 38px rgba(35, 54, 47, 0.08);
}

.module-header {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 22px;
  align-items: start;
  margin-bottom: 22px;
}

.compact-header {
  grid-template-columns: 1fr;
}

.module-header h3 {
  margin: 0 0 10px;
  color: #23362f;
  font-size: 28px;
  line-height: 1.22;
}

.module-tabs {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 10px;
  max-width: 600px;
}

.module-tabs button {
  min-height: 40px;
  padding: 0 16px;
  border-radius: 999px;
  border: 1px solid rgba(188, 174, 154, 0.9);
  background: rgba(255, 255, 255, 0.68);
  color: #23362f;
  font-size: 14px;
  font-weight: 650;
  cursor: pointer;
  transition:
    transform 0.18s ease,
    box-shadow 0.18s ease,
    background 0.18s ease;
}

.module-tabs button:hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 18px rgba(35, 54, 47, 0.08);
}

.module-tabs button.active {
  color: #fffaf2;
  background: #1f7a6b;
  border-color: #1f7a6b;
  box-shadow: 0 10px 22px rgba(31, 122, 107, 0.2);
}

.chart-display {
  width: 100%;
  max-width: 1180px;
  overflow: hidden;
  margin: 0 auto;
  border-radius: 24px;
  background: #f1ebe2;
  border: 1px solid #bcae9a;
  box-shadow:
    inset 0 0 0 1px rgba(255, 255, 255, 0.42),
    0 10px 24px rgba(35, 54, 47, 0.05);
}

.chart-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 18px;
  border-bottom: 1px solid rgba(188, 174, 154, 0.65);
  background: rgba(255, 255, 255, 0.55);
}

.chart-topbar strong {
  display: block;
  color: #23362f;
  font-size: 16px;
}

.chart-topbar span {
  padding: 8px 12px;
  border-radius: 999px;
  color: #23362f;
  background: rgba(255, 255, 255, 0.78);
  border: 1px solid rgba(188, 174, 154, 0.86);
  font-size: 13px;
  font-weight: 700;
  white-space: nowrap;
}

.chart-frame {
  display: block;
  width: 100%;
  border: 0;
  background: #f1ebe2;
}

.frame-short {
  height: 720px;
}


.frame-medium {
  height: 920px;
}

.frame-tall {
  height: 980px;
}

.analysis-note,
.overview-note {
  max-width: 1180px;
  margin: 16px auto 0;
  padding: 16px 18px;
  border-left: 4px solid #c06a42;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.58);
  border-top: 1px solid rgba(188, 174, 154, 0.72);
  border-right: 1px solid rgba(188, 174, 154, 0.52);
  border-bottom: 1px solid rgba(188, 174, 154, 0.52);
  color: #53645b;
  line-height: 1.72;
  font-size: 15px;
}

.analysis-note p {
  margin: 0;
}

.analysis-note p + p {
  margin-top: 8px;
}

.analysis-conclusion {
  color: #23362f;
  font-weight: 600;
}

.animated-chart {
  padding: 14px;
  border-radius: 24px;
  background: #f1ebe2;
  border: 1px solid #bcae9a;
  box-shadow:
    inset 0 0 0 1px rgba(255, 255, 255, 0.42),
    0 10px 24px rgba(35, 54, 47, 0.05);
}

@media (max-width: 1180px) {
  .module-header,
  .analysis-hero {
    grid-template-columns: 1fr;
  }

  .module-tabs {
    justify-content: flex-start;
    max-width: none;
  }
}

@media (max-width: 760px) {
  .analysis-hero,
  .main-module,
  .interactive-module {
    padding: 20px;
  }

  .hero-copy h2 {
    font-size: 29px;
  }

  .module-header h3 {
    font-size: 23px;
  }


  .chart-topbar {
    align-items: flex-start;
    flex-direction: column;
  }

  .frame-short,
  .frame-medium,
  .frame-tall {
    height: 760px;
  }
}
</style>
