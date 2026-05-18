<template>
  <section class="panel-card section-card curve-summary-section">
    <div class="section-heading summary-heading">
      <div>
        <p class="viz-kicker">Curve fit analysis</p>
        <h2>Statistical Summary of Curve Fitting</h2>
      </div>
    </div>

    <article class="viz-card viz-card-wide fit-chart-card">
      <div class="viz-toolbar">
        <div>
          <p class="viz-kicker">Main fitted view</p>
          <h4>Observed vs fitted rollout trajectories</h4>
        </div>
        <div class="segment-control">
          <button
            v-for="option in chartMetricOptions"
            :key="`chart-${option.key}`"
            type="button"
            class="segment-button"
            :class="{ active: selectedChartMetric === option.key }"
            @click="selectedChartMetric = option.key"
          >
            {{ option.label }}
          </button>
        </div>
      </div>

      <p class="model-note">
        Representative groups are shown as compact multiples. Solid lines are fitted values, dots are observed values,
        red markers indicate the steepest fitted growth quarter, and green guides mark fitted plateau entry.
      </p>

      <div v-if="chartSeries.length" class="fit-chart-shell">
        <svg class="fit-main-chart" viewBox="0 0 980 560" role="img" aria-label="Representative curve fitting chart">
          <g
            v-for="series in chartSeries"
            :key="series.group"
            class="fit-panel"
            :class="{ muted: activeChartGroup && activeChartGroup !== series.group, active: activeChartGroup === series.group }"
            @mouseenter="activeChartGroup = series.group"
            @mouseleave="activeChartGroup = ''"
          >
            <rect class="fit-panel-bg" :x="series.panel.left - 16" :y="series.panel.top - 24" :width="series.panel.width + 30" :height="series.panel.height + 58" rx="10" />
            <text class="fit-panel-title" :x="series.panel.left" :y="series.panel.top - 8">{{ series.group }}</text>
            <text class="fit-panel-meta" :x="series.panel.right" :y="series.panel.top - 8" text-anchor="end">
              {{ modelLabel(series.bestModel) }} · R² {{ formatDecimal(series.r2, 3) }}
            </text>

            <line v-for="tick in chartYTicks" :key="`${series.group}-grid-${tick}`" class="mini-grid" :x1="series.panel.left" :x2="series.panel.right" :y1="panelY(series.panel, tick)" :y2="panelY(series.panel, tick)" />
            <line class="mini-axis" :x1="series.panel.left" :x2="series.panel.right" :y1="series.panel.bottom" :y2="series.panel.bottom" />
            <line class="mini-axis" :x1="series.panel.left" :x2="series.panel.left" :y1="series.panel.top" :y2="series.panel.bottom" />

            <line v-if="series.plateauQuarter" class="plateau-guide" :x1="panelX(series.panel, series.plateauQuarter)" :x2="panelX(series.panel, series.plateauQuarter)" :y1="series.panel.top" :y2="series.panel.bottom" />
            <line v-if="series.peakQuarter" class="peak-guide" :x1="panelX(series.panel, series.peakQuarter)" :x2="panelX(series.panel, series.peakQuarter)" :y1="series.panel.top" :y2="series.panel.bottom" />

            <path class="fit-line observed-line" :d="panelPath(series.panel, series.observedPoints)" />
            <path class="fit-line fitted-line" :d="panelPath(series.panel, series.fittedPoints)" :stroke="series.color" />

            <circle v-for="point in series.observedPoints" :key="`${series.group}-obs-${point.quarter}`" class="observed-point" :cx="panelX(series.panel, point.quarter)" :cy="panelY(series.panel, point.value)" r="3.2" />
            <circle v-if="series.peakPoint" class="peak-point" :cx="panelX(series.panel, series.peakPoint.quarter)" :cy="panelY(series.panel, series.peakPoint.value)" r="5" />

            <text v-for="quarter in visibleChartQuarters" :key="`${series.group}-x-${quarter}`" class="mini-label" :x="panelX(series.panel, quarter)" :y="series.panel.bottom + 18" text-anchor="middle">{{ quarter }}</text>
            <text class="mini-label" :x="series.panel.left - 8" :y="panelY(series.panel, 1) + 4" text-anchor="end">100%</text>
            <text class="mini-label" :x="series.panel.left - 8" :y="panelY(series.panel, 0.5) + 4" text-anchor="end">50%</text>
          </g>
        </svg>

        <div class="fit-chart-legend">
          <span><i class="legend-line fitted"></i> Fitted</span>
          <span><i class="legend-dot observed"></i> Observed</span>
          <span><i class="legend-dot peak"></i> Peak growth</span>
          <span><i class="legend-line plateau"></i> Plateau entry</span>
        </div>
      </div>
      <p v-else class="empty-state">No fitted values are available for the selected metric.</p>
    </article>

    <article class="viz-card viz-card-wide summary-card">
      <div class="viz-toolbar">
        <div>
          <p class="viz-kicker">Modeling summary</p>
          <h4>Curve-fit Summary Panel</h4>
        </div>
        <div class="summary-actions">
          <div class="segment-control">
            <button
              v-for="option in tableMetricOptions"
              :key="`table-${option.key}`"
              type="button"
              class="segment-button"
              :class="{ active: selectedTableMetric === option.key }"
              @click="selectedTableMetric = option.key"
            >
              {{ option.label }}
            </button>
          </div>
          <div class="summary-count">{{ filteredSummaryRows.length }} rows</div>
        </div>
      </div>

      <div class="model-distribution">
        <article v-for="item in modelDistribution" :key="item.metric" class="model-chip-card">
          <span>{{ labelForMetric(item.metric) }}</span>
          <strong>{{ item.winner }}</strong>
          <div class="model-badges">
            <i>Gompertz {{ item.gompertz }}</i>
            <i>Logistic {{ item.logistic }}</i>
          </div>
        </article>
      </div>
      <p class="model-note">{{ distributionNarrative }}</p>

      <div class="summary-table-wrap">
        <table class="summary-table">
          <thead>
            <tr>
              <th>Group</th>
              <th>Metric</th>
              <th>Best model</th>
              <th>R²</th>
              <th>RMSE</th>
              <th>Main takeaway</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in filteredSummaryRows" :key="`${row.group}-${row.metric}`">
              <td>
                <strong>{{ row.group }}</strong>
              </td>
              <td>{{ labelForMetric(row.metric) }}</td>
              <td>
                <span class="model-pill" :class="row.bestModel">{{ modelLabel(row.bestModel) }}</span>
              </td>
              <td>
                <span class="score-pill" :class="fitQualityClass(row.r2)">{{ formatDecimal(row.r2, 3) }}</span>
              </td>
              <td>{{ formatDecimal(row.rmse, 3) }}</td>
              <td :title="`${row.growthSummary} ${row.timingSummary}`">{{ row.takeaway }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </article>

    <div class="finding-grid compact-findings">
      <article v-for="finding in compactFindings" :key="finding.title" class="finding-card compact">
        <p class="viz-kicker">{{ finding.kicker }}</p>
        <h4>{{ finding.title }}</h4>
        <p>{{ finding.text }}</p>
      </article>
    </div>

    <p v-if="loadWarnings.length" class="data-warning">Data notes: {{ loadWarnings.join(" | ") }}</p>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { loadCsvFromCandidates, pickField, toNumber, unique } from "../../utils/csv";

const tableMetricOptions = [
  { key: "first_dose_progress", label: "First dose" },
  { key: "full_vaccination_progress", label: "Full vaccination" },
];

const chartMetricOptions = [
  { key: "first_dose_progress", label: "First dose" },
  { key: "full_vaccination_progress", label: "Full vaccination" },
];

const representativeGroups = [
  "Africa",
  "Asia",
  "Europe",
  "North America",
  "High-income countries",
  "Low-income countries",
];
const chartPalette = ["#1d6b57", "#4f76b4", "#b85c38", "#c47b2f", "#506f97", "#875167"];
const chartYTicks = [0, 0.5, 1];
const chartPanelLayout = {
  width: 250,
  height: 128,
  xGap: 62,
  yGap: 74,
  left: 76,
  top: 70,
};
const MAX_QUARTER = "2023Q4";

const datasets = ref({
  summary: [],
  values: [],
});
const loadWarnings = ref([]);
const selectedTableMetric = ref("first_dose_progress");
const selectedChartMetric = ref("first_dose_progress");
const activeChartGroup = ref("");

onMounted(async () => {
  const [summary, values] = await Promise.all([
    loadCsvFromCandidates(["group_curve_fit_summary.csv"], "/analysis1"),
    loadCsvFromCandidates(["group_curve_fit_values.csv"], "/analysis1"),
  ]);

  datasets.value = {
    summary: summary.rows,
    values: values.rows,
  };

  loadWarnings.value = [summary, values].map((item) => item.error).filter(Boolean);
});

const rawSummaryRows = computed(() =>
  datasets.value.summary
    .map((row) => ({
      group: pickField(row, ["country", "group"]),
      metric: pickField(row, ["metric"]),
      bestModel: String(pickField(row, ["best_model", "model"])).toLowerCase(),
      r2: toNumber(pickField(row, ["r2"])),
      rmse: toNumber(pickField(row, ["rmse"])),
      mae: toNumber(pickField(row, ["mae"])),
      param1: toNumber(pickField(row, ["param_1", "param1"])),
      param2: toNumber(pickField(row, ["param_2", "param2"])),
      param3: toNumber(pickField(row, ["param_3", "param3"])),
    }))
    .filter((row) => row.group && row.metric && row.bestModel)
);

const valueRows = computed(() =>
  datasets.value.values
    .map((row) => {
      const metric = pickField(row, ["metric"]);
      return {
        t: toNumber(pickField(row, ["t"])),
        group: pickField(row, ["country", "group"]),
        metric,
        model: String(pickField(row, ["model", "best_model"])).toLowerCase(),
        quarter: pickField(row, ["quarter", "quarter_period"]),
        yhat: toNumber(pickField(row, ["yhat"])),
        observed: toNumber(pickField(row, [metric])),
      };
    })
    .filter((row) => row.group && row.metric && row.quarter && Number.isFinite(row.yhat))
);

const enrichedSummaryRows = computed(() =>
  rawSummaryRows.value
    .map((row) => {
      const curve = curveStats(row);
      return {
        ...row,
        ...curve,
        growthSummary: buildGrowthSummary(row, curve),
        timingSummary: buildTimingSummary(row, curve),
        takeaway: buildTakeaway(row, curve),
      };
    })
    .sort((left, right) => {
      if (left.metric !== right.metric) {
        return left.metric.localeCompare(right.metric);
      }
      return left.group.localeCompare(right.group);
    })
);

const filteredSummaryRows = computed(() => {
  return enrichedSummaryRows.value.filter((row) => row.metric === selectedTableMetric.value);
});

const chartQuarters = computed(() =>
  unique(valueRows.value.map((row) => row.quarter))
    .filter((quarter) => quarter && isQuarterOnOrBefore(quarter, MAX_QUARTER))
    .sort(sortQuarterKeys)
);

const visibleChartQuarters = computed(() => {
  if (!chartQuarters.value.length) {
    return [];
  }
  return [
    chartQuarters.value[0],
    chartQuarters.value[Math.floor(chartQuarters.value.length / 2)],
    chartQuarters.value[chartQuarters.value.length - 1],
  ]
    .filter(Boolean)
    .filter((quarter, index, list) => list.indexOf(quarter) === index);
});

const chartSeries = computed(() =>
  representativeGroups
    .map((group, index) => {
      const summary = enrichedSummaryRows.value.find((row) => row.group === group && row.metric === selectedChartMetric.value);
      if (!summary) {
        return null;
      }

      const rows = valueRows.value
        .filter(
          (row) =>
            row.group === group &&
            row.metric === selectedChartMetric.value &&
            row.model === summary.bestModel &&
            isQuarterOnOrBefore(row.quarter, MAX_QUARTER)
        )
        .sort((left, right) => sortQuarterKeys(left.quarter, right.quarter));

      if (!rows.length) {
        return null;
      }

      const panel = panelForIndex(index);
      const peakPoint = rows.find((row) => row.quarter === summary.peakQuarter);

      return {
        group,
        color: chartPalette[index % chartPalette.length],
        bestModel: summary.bestModel,
        r2: summary.r2,
        peakQuarter: summary.peakQuarter,
        plateauQuarter: summary.plateauQuarter,
        peakPoint: peakPoint ? { quarter: peakPoint.quarter, value: clamp01(peakPoint.yhat) } : null,
        panel,
        observedPoints: rows.filter((row) => Number.isFinite(row.observed)).map((row) => ({ quarter: row.quarter, value: clamp01(row.observed) })),
        fittedPoints: rows.map((row) => ({ quarter: row.quarter, value: clamp01(row.yhat) })),
      };
    })
    .filter(Boolean)
);

const modelDistribution = computed(() =>
  ["first_dose_progress", "full_vaccination_progress"].map((metric) => {
    const rows = rawSummaryRows.value.filter((row) => row.metric === metric);
    const gompertz = rows.filter((row) => row.bestModel === "gompertz").length;
    const logistic = rows.filter((row) => row.bestModel === "logistic").length;
    let winner = "Balanced";
    if (gompertz > logistic) {
      winner = "Gompertz more common";
    } else if (logistic > gompertz) {
      winner = "Logistic more common";
    }
    return { metric, gompertz, logistic, winner };
  })
);

const distributionNarrative = computed(() => {
  const first = modelDistribution.value.find((item) => item.metric === "first_dose_progress");
  const full = modelDistribution.value.find((item) => item.metric === "full_vaccination_progress");
  if (!first || !full) {
    return "Model-family counts are unavailable until the summary table loads.";
  }
  return `First-dose progress is best fit more often by ${winnerName(first)}, while full-vaccination progress is best fit more often by ${winnerName(full)}. These counts summarize model choice only; parameter values are interpreted conservatively within each model family.`;
});

const compactFindings = computed(() => {
  const rows = enrichedSummaryRows.value;
  if (!rows.length) {
    return [];
  }

  const strongest = [...rows].filter((row) => Number.isFinite(row.r2)).sort((left, right) => right.r2 - left.r2)[0];
  const earliest = [...rows]
    .filter((row) => Number.isFinite(row.peakT))
    .sort((left, right) => left.peakT - right.peakT || right.peakDelta - left.peakDelta)[0];
  const widestGapMetric = modelDistribution.value
    .map((item) => ({ ...item, gap: Math.abs(item.gompertz - item.logistic) }))
    .sort((left, right) => right.gap - left.gap)[0];

  return [
    {
      kicker: "Strongest fit",
      title: strongest?.group || "No fit",
      text: strongest
        ? `${labelForMetric(strongest.metric)} has the highest R² (${formatDecimal(strongest.r2, 3)}) with a ${modelLabel(strongest.bestModel)} fit, indicating a highly regular cumulative growth pattern.`
        : "No fitted rows are available.",
    },
    {
      kicker: "Earliest transition",
      title: earliest?.group || "No timing signal",
      text: earliest
        ? `${labelForMetric(earliest.metric)} reaches its steepest fitted growth around ${earliest.peakQuarter}. This is estimated from the largest quarter-to-quarter change in fitted values.`
        : "The fitted values do not contain enough adjacent quarters to estimate transition timing.",
    },
    {
      kicker: "Model family",
      title: widestGapMetric ? labelForMetric(widestGapMetric.metric) : "No model split",
      text: widestGapMetric
        ? `${winnerName(widestGapMetric)} appears most often for this metric (${widestGapMetric.gompertz} Gompertz vs ${widestGapMetric.logistic} Logistic), suggesting a visible model-family preference.`
        : "Model-family distribution is unavailable.",
    },
  ];
});

function curveStats(summaryRow) {
  const rows = valueRows.value
    .filter(
      (row) =>
        row.group === summaryRow.group &&
        row.metric === summaryRow.metric &&
        (!summaryRow.bestModel || row.model === summaryRow.bestModel) &&
        isQuarterOnOrBefore(row.quarter, MAX_QUARTER)
    )
    .sort((left, right) => left.t - right.t);

  if (!rows.length) {
    return {
      peakQuarter: "",
      peakDelta: null,
      peakT: null,
      plateauQuarter: "",
      finalObserved: null,
      finalFitted: null,
    };
  }

  let peak = null;
  for (let index = 1; index < rows.length; index += 1) {
    const previous = rows[index - 1];
    const current = rows[index];
    const delta = current.yhat - previous.yhat;
    if (!peak || delta > peak.delta) {
      peak = { quarter: current.quarter, delta, t: current.t };
    }
  }

  const target = Number.isFinite(summaryRow.param1) ? summaryRow.param1 * 0.95 : 0.95;
  const plateau = rows.find((row) => row.yhat >= target);
  const final = rows[rows.length - 1];

  return {
    peakQuarter: peak?.quarter || "",
    peakDelta: peak?.delta ?? null,
    peakT: peak?.t ?? null,
    plateauQuarter: plateau?.quarter || "",
    finalObserved: final?.observed ?? null,
    finalFitted: final?.yhat ?? null,
  };
}

function buildGrowthSummary(row, curve) {
  const fit = fitQualityLabel(row.r2);
  const steepness = Number.isFinite(curve.peakDelta)
    ? `${formatPercentPoint(curve.peakDelta)} fitted QoQ peak`
    : "limited adjacent fitted values";

  if (row.bestModel === "gompertz") {
    return `${fit}; asymmetric growth shape, ${steepness}.`;
  }
  if (row.bestModel === "logistic") {
    return `${fit}; smoother S-curve shape, ${steepness}.`;
  }
  return `${fit}; fitted growth pattern summarized from yhat values.`;
}

function buildTimingSummary(row, curve) {
  const timingHint =
    row.bestModel === "gompertz"
      ? "Gompertz timing parameter gives a within-model phase hint"
      : row.bestModel === "logistic"
        ? "Logistic midpoint parameter gives a within-model phase hint"
        : "Timing parameter is model-specific";

  const peak = curve.peakQuarter ? `steepest fitted change near ${curve.peakQuarter}` : "no stable peak-change quarter";
  const plateau = curve.plateauQuarter ? `95% fitted plateau by ${curve.plateauQuarter}` : "plateau not reached in fitted range";
  return `${peak}; ${plateau}. ${timingHint}.`;
}

function buildTakeaway(row, curve) {
  const strongFit = Number.isFinite(row.r2) && row.r2 >= 0.995;
  const lowError = Number.isFinite(row.rmse) && row.rmse <= 0.02;
  const earlyPeak = Number.isFinite(curve.peakT) && curve.peakT <= 4;
  const latePeak = Number.isFinite(curve.peakT) && curve.peakT >= 7;

  if (strongFit && lowError && earlyPeak) {
    return "Steep early growth with strong fit.";
  }
  if (strongFit && lowError) {
    return "Highly regular cumulative growth pattern.";
  }
  if (earlyPeak) {
    return "Earlier phase transition and rapid saturation.";
  }
  if (latePeak) {
    return "Slower takeoff with later fitted acceleration.";
  }
  if (Number.isFinite(row.r2) && row.r2 < 0.985) {
    return "Less regular trajectory; fit captures broad direction.";
  }
  return "Smooth fitted progression with moderate timing signal.";
}

function winnerName(item) {
  if (!item) {
    return "neither model family";
  }
  if (item.gompertz > item.logistic) {
    return "Gompertz";
  }
  if (item.logistic > item.gompertz) {
    return "Logistic";
  }
  return "neither model family";
}

function fitQualityLabel(value) {
  if (!Number.isFinite(value)) {
    return "fit quality unavailable";
  }
  if (value >= 0.995) {
    return "excellent fit";
  }
  if (value >= 0.985) {
    return "strong fit";
  }
  return "moderate fit";
}

function fitQualityClass(value) {
  if (!Number.isFinite(value)) {
    return "neutral";
  }
  if (value >= 0.995) {
    return "high";
  }
  if (value >= 0.985) {
    return "mid";
  }
  return "low";
}

function modelLabel(model) {
  return model ? model.charAt(0).toUpperCase() + model.slice(1) : "N/A";
}

function labelForMetric(metric) {
  return metric === "first_dose_progress" ? "First-dose progress" : "Full-vaccination progress";
}

function formatDecimal(value, digits = 3) {
  return Number.isFinite(value) ? value.toFixed(digits) : "N/A";
}

function formatPercentPoint(value) {
  return Number.isFinite(value) ? `${(value * 100).toFixed(1)} pts` : "N/A";
}

function panelForIndex(index) {
  const column = index % 3;
  const row = Math.floor(index / 3);
  const left = chartPanelLayout.left + column * (chartPanelLayout.width + chartPanelLayout.xGap);
  const top = chartPanelLayout.top + row * (chartPanelLayout.height + chartPanelLayout.yGap);
  return {
    left,
    top,
    width: chartPanelLayout.width,
    height: chartPanelLayout.height,
    right: left + chartPanelLayout.width,
    bottom: top + chartPanelLayout.height,
  };
}

function panelX(panel, quarter) {
  const index = chartQuarters.value.indexOf(quarter);
  if (index < 0 || chartQuarters.value.length <= 1) {
    return panel.left;
  }
  return panel.left + (index / (chartQuarters.value.length - 1)) * panel.width;
}

function panelY(panel, value) {
  const ratio = Math.max(0, Math.min(1, value));
  return panel.bottom - ratio * panel.height;
}

function panelPath(panel, points) {
  if (!points.length) {
    return "";
  }
  return points.map((point, index) => `${index === 0 ? "M" : "L"} ${panelX(panel, point.quarter)} ${panelY(panel, point.value)}`).join(" ");
}

function clamp01(value) {
  return Math.max(0, Math.min(1, value));
}

function sortQuarterKeys(left, right) {
  const leftMatch = String(left || "").match(/^(\d{4})Q(\d)$/);
  const rightMatch = String(right || "").match(/^(\d{4})Q(\d)$/);
  if (!leftMatch || !rightMatch) {
    return String(left || "").localeCompare(String(right || ""));
  }
  const leftYear = Number(leftMatch[1]);
  const rightYear = Number(rightMatch[1]);
  if (leftYear !== rightYear) {
    return leftYear - rightYear;
  }
  return Number(leftMatch[2]) - Number(rightMatch[2]);
}

function quarterOrdinal(quarter) {
  const match = String(quarter || "").match(/^(\d{4})Q(\d)$/);
  if (!match) {
    return null;
  }
  return Number(match[1]) * 4 + Number(match[2]) - 1;
}

function isQuarterOnOrBefore(quarter, maxQuarter) {
  const quarterValue = quarterOrdinal(quarter);
  const maxValue = quarterOrdinal(maxQuarter);
  return Number.isFinite(quarterValue) && Number.isFinite(maxValue) && quarterValue <= maxValue;
}
</script>

<style scoped>
.curve-summary-section {
  display: grid;
  gap: 1rem;
  animation: summary-in 0.35s ease both;
}

.summary-heading {
  align-items: flex-start;
}

.body-note {
  margin-top: -0.1rem;
  max-width: 1120px;
  line-height: 1.56;
}

.fit-chart-card,
.summary-card {
  padding: 0.95rem;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.58);
}

.fit-chart-shell {
  display: grid;
  gap: 0.7rem;
}

.fit-main-chart {
  width: 100%;
  height: auto;
  display: block;
}

.fit-panel {
  opacity: 1;
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.fit-panel.muted {
  opacity: 0.32;
}

.fit-panel.active {
  opacity: 1;
}

.fit-panel-bg {
  fill: rgba(255, 250, 242, 0.72);
  stroke: rgba(31, 42, 31, 0.08);
  transition: fill 0.18s ease, stroke 0.18s ease;
}

.fit-panel.active .fit-panel-bg {
  fill: rgba(255, 250, 242, 0.95);
  stroke: rgba(29, 107, 87, 0.22);
}

.fit-panel-title {
  fill: var(--ink);
  font-size: 13px;
  font-weight: 800;
}

.fit-panel-meta,
.mini-label {
  fill: var(--muted);
  font-size: 10px;
}

.mini-grid {
  stroke: rgba(31, 42, 31, 0.08);
  stroke-width: 1;
}

.mini-axis {
  stroke: rgba(31, 42, 31, 0.24);
  stroke-width: 1.15;
}

.fit-line {
  fill: none;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.observed-line {
  stroke: rgba(31, 42, 31, 0.34);
  stroke-width: 1.6;
  stroke-dasharray: 3 5;
}

.fitted-line {
  stroke-width: 3;
}

.observed-point {
  fill: #fffaf2;
  stroke: rgba(31, 42, 31, 0.48);
  stroke-width: 1.35;
}

.peak-guide {
  stroke: rgba(209, 73, 63, 0.42);
  stroke-width: 1.3;
  stroke-dasharray: 4 5;
}

.plateau-guide {
  stroke: rgba(29, 107, 87, 0.38);
  stroke-width: 1.3;
  stroke-dasharray: 6 5;
}

.peak-point {
  fill: #d1493f;
  stroke: #fffaf2;
  stroke-width: 2;
}

.fit-chart-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 0.7rem;
  color: var(--muted);
  font-size: 0.84rem;
}

.fit-chart-legend span {
  display: inline-flex;
  align-items: center;
  gap: 0.36rem;
}

.legend-line,
.legend-dot {
  display: inline-block;
  flex: none;
}

.legend-line {
  width: 20px;
  height: 3px;
  border-radius: 999px;
}

.legend-line.fitted {
  background: #1d6b57;
}

.legend-line.plateau {
  height: 12px;
  width: 2px;
  background: #1d6b57;
}

.legend-dot {
  width: 9px;
  height: 9px;
  border-radius: 999px;
}

.legend-dot.observed {
  background: #fffaf2;
  border: 1px solid rgba(31, 42, 31, 0.48);
}

.legend-dot.peak {
  background: #d1493f;
}

.summary-count {
  padding: 0.34rem 0.58rem;
  border-radius: 999px;
  background: rgba(29, 107, 87, 0.1);
  color: #1d6b57;
  font-size: 0.82rem;
  font-weight: 800;
}

.summary-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  align-items: center;
  gap: 0.55rem;
}

.model-distribution {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.75rem;
  margin-bottom: 0.55rem;
}

.model-chip-card {
  display: grid;
  gap: 0.42rem;
  padding: 0.82rem 0.88rem;
  border: 1px solid rgba(31, 42, 31, 0.08);
  border-radius: 12px;
  background: rgba(255, 250, 242, 0.82);
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}

.model-chip-card:hover,
.finding-card.compact:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 22px rgba(31, 42, 31, 0.08);
}

.model-chip-card span {
  color: var(--muted);
  font-size: 0.86rem;
}

.model-chip-card strong {
  color: var(--ink);
  font-size: 1rem;
}

.model-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}

.model-badges i {
  font-style: normal;
  padding: 0.24rem 0.46rem;
  border-radius: 999px;
  background: rgba(29, 107, 87, 0.1);
  color: #1d6b57;
  font-size: 0.78rem;
  font-weight: 700;
}

.model-note {
  margin: 0 0 0.8rem;
  color: var(--muted);
  line-height: 1.5;
}

.summary-table-wrap {
  overflow-x: auto;
  border: 1px solid rgba(31, 42, 31, 0.08);
  border-radius: 12px;
  background: rgba(255, 250, 242, 0.68);
}

.summary-table {
  width: 100%;
  min-width: 860px;
  border-collapse: separate;
  border-spacing: 0;
}

.summary-table th,
.summary-table td {
  padding: 0.72rem 0.78rem;
  text-align: left;
  vertical-align: top;
  border-bottom: 1px solid rgba(31, 42, 31, 0.07);
}

.summary-table th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: rgba(245, 239, 228, 0.98);
  color: #304238;
  font-size: 0.76rem;
  letter-spacing: 0.07em;
  text-transform: uppercase;
}

.summary-table td {
  color: var(--muted);
  font-size: 0.87rem;
  line-height: 1.38;
}

.summary-table td:first-child,
.summary-table td:nth-child(2),
.summary-table td:nth-child(3),
.summary-table td:nth-child(4),
.summary-table td:nth-child(5) {
  white-space: nowrap;
}

.summary-table td strong {
  color: var(--ink);
}

.summary-table tbody tr {
  transition: background-color 0.18s ease;
}

.summary-table tbody tr:hover {
  background: rgba(29, 107, 87, 0.055);
}

.model-pill,
.score-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 72px;
  padding: 0.24rem 0.46rem;
  border-radius: 999px;
  font-size: 0.76rem;
  font-weight: 800;
}

.model-pill.gompertz {
  background: rgba(29, 107, 87, 0.12);
  color: #1d6b57;
}

.model-pill.logistic {
  background: rgba(184, 92, 56, 0.13);
  color: #934529;
}

.score-pill.high {
  background: rgba(29, 107, 87, 0.13);
  color: #1d6b57;
}

.score-pill.mid {
  background: rgba(196, 123, 47, 0.14);
  color: #8a5a24;
}

.score-pill.low,
.score-pill.neutral {
  background: rgba(31, 42, 31, 0.08);
  color: var(--muted);
}

.compact-findings {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.85rem;
}

.finding-card.compact {
  padding: 0.92rem 0.95rem;
  border-radius: 14px;
  background: rgba(255, 250, 242, 0.78);
  border: 1px solid rgba(31, 42, 31, 0.08);
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}

.finding-card.compact h4 {
  margin: 0.28rem 0 0.42rem;
  font-size: 1rem;
}

.finding-card.compact p:last-child {
  margin: 0;
  color: var(--muted);
  line-height: 1.48;
}

.data-warning {
  margin: 0;
  color: var(--muted);
  font-size: 0.92rem;
}

@keyframes summary-in {
  from {
    opacity: 0;
    transform: translateY(8px);
  }

  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 960px) {
  .model-distribution,
  .compact-findings {
    grid-template-columns: 1fr;
  }
}
</style>
