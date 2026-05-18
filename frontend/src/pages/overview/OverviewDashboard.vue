<template>
  <section class="panel-card overview-shell">
    <div class="overview-topbar">
      <div>
        <p class="viz-kicker">Global lens</p>
        <h2>Quarterly vaccination and case situation</h2>
      </div>
      <div class="timeline-controls">
        <label class="control-stack slider-stack">
          <span>Quarter</span>
          <input v-model.number="selectedQuarterIndex" type="range" min="0" :max="Math.max(0, globalQuarters.length - 1)" />
        </label>
        <div class="focus-chip quarter-chip">{{ selectedGlobalQuarter || "No quarter" }}</div>
      </div>
    </div>

    <div class="overview-cards">
      <article class="overview-stat-card">
        <p class="viz-kicker">Vaccination leader</p>
        <h3>{{ vaccinationLeaderCard.title }}</h3>
        <p>{{ vaccinationLeaderCard.value }}</p>
      </article>
      <article class="overview-stat-card">
        <p class="viz-kicker">Case hotspot</p>
        <h3>{{ caseLeaderCard.title }}</h3>
        <p>{{ caseLeaderCard.value }}</p>
      </article>
      <article class="overview-stat-card">
        <p class="viz-kicker">Fastest group</p>
        <h3>{{ groupLeaderCard.title }}</h3>
        <p>{{ groupLeaderCard.value }}</p>
      </article>
      <article class="overview-stat-card">
        <p class="viz-kicker">Milestone pace</p>
        <h3>{{ milestoneLeaderCard.title }}</h3>
        <p>{{ milestoneLeaderCard.value }}</p>
      </article>
    </div>
  </section>

  <section class="panel-card overview-section">
    <article class="viz-card viz-card-wide">
      <div class="viz-toolbar">
        <div>
          <p class="viz-kicker">Overview 1</p>
          <h4>Global Vaccination Status Overview</h4>
        </div>
        <div class="segment-control">
          <button
            v-for="option in vaccinationMetricOptions"
            :key="option.key"
            type="button"
            class="segment-button"
            :class="{ active: selectedVaccinationMetric === option.key }"
            @click="selectedVaccinationMetric = option.key"
          >
            {{ option.label }}
          </button>
        </div>
      </div>
      <p class="viz-chart-intro">
        This large ranking view replaces the unstable map renderer while keeping the same quarter-level comparison logic.
        Each bar shows one country's vaccination status proxy in the selected quarter, so the page stays readable and fast.
      </p>
      <div v-if="vaccinationRankedRows.length" class="ranking-stack">
        <article
          v-for="row in vaccinationRankedRows"
          :key="`vacc-${row.country}`"
          class="ranking-row ranking-row-vaccination"
        >
          <div class="ranking-meta">
            <strong>{{ row.country }}</strong>
            <span>{{ selectedGlobalQuarter }}</span>
          </div>
          <div class="ranking-bar-track">
            <div class="ranking-bar ranking-bar-vaccination" :style="{ width: `${row.width}%` }"></div>
          </div>
          <div class="ranking-value">{{ selectedVaccinationMetricMeta.formatter(row.value) }}</div>
        </article>
      </div>
      <p v-else class="empty-state">No vaccination rows are available for the selected quarter.</p>
      <div class="viz-footnote">
        <p>{{ vaccinationNarrative }}</p>
      </div>
    </article>

    <article class="viz-card viz-card-wide">
      <div class="viz-toolbar">
        <div>
          <p class="viz-kicker">Overview 2</p>
          <h4>Global Case Statistics Overview</h4>
        </div>
        <div class="segment-control">
          <button
            v-for="option in caseMetricOptions"
            :key="option.key"
            type="button"
            class="segment-button"
            :class="{ active: selectedCaseMetric === option.key }"
            @click="selectedCaseMetric = option.key"
          >
            {{ option.label }}
          </button>
        </div>
      </div>
      <p class="viz-chart-intro">
        This panel focuses on relative case burden instead of a dense daily trend. It keeps the overview page stable and
        makes the quarter-to-quarter contrast immediately visible.
      </p>
      <div v-if="caseRankedRows.length" class="ranking-stack">
        <article
          v-for="row in caseRankedRows"
          :key="`case-${row.country}`"
          class="ranking-row ranking-row-case"
        >
          <div class="ranking-meta">
            <strong>{{ row.country }}</strong>
            <span>{{ selectedGlobalQuarter }}</span>
          </div>
          <div class="ranking-bar-track">
            <div class="ranking-bar ranking-bar-case" :style="{ width: `${row.width}%` }"></div>
          </div>
          <div class="ranking-value">{{ selectedCaseMetricMeta.formatter(row.value) }}</div>
        </article>
      </div>
      <p v-else class="empty-state">No case rows are available for the selected quarter.</p>
      <div class="viz-footnote">
        <p>{{ caseNarrative }}</p>
      </div>
    </article>

    <article class="viz-card viz-card-wide">
      <div class="viz-toolbar">
        <div>
          <p class="viz-kicker">Matrix</p>
          <h4>Cross-group Quarterly Vaccination Matrix</h4>
        </div>
        <div class="segment-control">
          <button
            v-for="option in groupMetricOptions"
            :key="option.key"
            type="button"
            class="segment-button"
            :class="{ active: selectedGroupMetric === option.key }"
            @click="selectedGroupMetric = option.key"
          >
            {{ option.label }}
          </button>
        </div>
      </div>
      <p class="viz-chart-intro">
        The matrix uses quarter on the x-axis, group on the y-axis, and color for the selected vaccination metric. It
        keeps the most important group-level timing story from the original redesign request.
      </p>
      <div v-if="groupMetricMatrix.groups.length" class="heatmap-wrap">
        <div class="heatmap-head" :style="heatmapGridStyle">
          <span></span>
          <span v-for="quarter in groupMetricMatrix.quarters" :key="quarter">{{ quarter }}</span>
        </div>
        <div
          v-for="group in groupMetricMatrix.groups"
          :key="group"
          class="heatmap-row"
          :style="heatmapGridStyle"
        >
          <strong>{{ group }}</strong>
          <div
            v-for="quarter in groupMetricMatrix.quarters"
            :key="`${group}-${quarter}`"
            class="heat-cell detailed-heat-cell"
            :style="{ background: groupCellColor(group, quarter) }"
            :title="groupCellTitle(group, quarter)"
          >
            <span>{{ groupCellLabel(group, quarter) }}</span>
          </div>
        </div>
      </div>
      <p v-else class="empty-state">No group-level quarterly data is available.</p>
      <div class="viz-footnote">
        <p>{{ groupNarrative }}</p>
      </div>
    </article>
  </section>

  <p v-if="loadWarnings.length" class="data-warning">Data notes: {{ loadWarnings.join(" | ") }}</p>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { formatCompactNumber, loadCsvFromCandidates, pickField, toNumber, unique } from "../../utils/csv";

const COUNTRY_ALIASES = {
  "Democratic Republic of Congo": "Democratic Republic of the Congo",
  "Republic of Congo": "Congo",
  "South Korea": "Korea, South",
  "North Korea": "Korea, North",
  Czechia: "Czech Republic",
  "Bosnia and Herzegovina": "Bosnia and Herz.",
  "North Macedonia": "Macedonia",
  "South Sudan": "S. Sudan",
  Eswatini: "Swaziland",
};

const vaccinationMetricOptions = [
  {
    key: "vacc_rollout_speed_avg",
    label: "Rollout speed",
    description: "quarter-average smoothed first-dose flow per hundred people",
    formatter: (value) => `${Number(value).toFixed(3)} / 100`,
  },
  {
    key: "vacc_rolling_6m_per_hundred",
    label: "6-month dose intensity",
    description: "quarter-end rolling vaccinations over the last 6 months per hundred people",
    formatter: (value) => `${Number(value).toFixed(1)} / 100`,
  },
  {
    key: "vacc_rolling_12m_per_hundred",
    label: "12-month dose intensity",
    description: "quarter-end rolling vaccinations over the last 12 months per hundred people",
    formatter: (value) => `${Number(value).toFixed(1)} / 100`,
  },
];

const caseMetricOptions = [
  {
    key: "cases_new_cases_pm7_avg",
    label: "7-day avg new cases",
    description: "quarter-average 7-day smoothed new cases per million",
    formatter: (value) => `${Number(value).toFixed(0)} / 1M`,
  },
  {
    key: "cases_new_cases_pm_avg",
    label: "Daily new cases",
    description: "quarter-average daily new cases per million",
    formatter: (value) => `${Number(value).toFixed(0)} / 1M`,
  },
  {
    key: "cases_total_cases_pm_latest",
    label: "Cumulative burden",
    description: "quarter-end cumulative cases per million",
    formatter: (value) => `${formatCompactNumber(Number(value), 1)} / 1M`,
  },
];

const groupMetricOptions = [
  { key: "rollout_speed", label: "Rollout speed", formatter: (value) => `${Number(value).toFixed(3)} / 100` },
  { key: "first_dose_progress", label: "First-dose progress", formatter: (value) => `${(Number(value) * 100).toFixed(1)}%` },
  { key: "full_vaccination_progress", label: "Full vaccination progress", formatter: (value) => `${(Number(value) * 100).toFixed(1)}%` },
];

const datasets = ref({
  countryQuarterly: [],
  groupQuarterlyLong: [],
  groupQuarterlyWide: [],
  groupMeta: [],
  groupSummary: [],
  groupMilestones: [],
});
const loadWarnings = ref([]);
const selectedVaccinationMetric = ref(vaccinationMetricOptions[2].key);
const selectedCaseMetric = ref(caseMetricOptions[0].key);
const selectedGroupMetric = ref(groupMetricOptions[0].key);
const selectedQuarterIndex = ref(0);

const selectedVaccinationMetricMeta = computed(
  () => vaccinationMetricOptions.find((option) => option.key === selectedVaccinationMetric.value) || vaccinationMetricOptions[0]
);
const selectedCaseMetricMeta = computed(
  () => caseMetricOptions.find((option) => option.key === selectedCaseMetric.value) || caseMetricOptions[0]
);
const selectedGroupMetricMeta = computed(
  () => groupMetricOptions.find((option) => option.key === selectedGroupMetric.value) || groupMetricOptions[0]
);

onMounted(async () => {
  const [countryQuarterly, groupQuarterlyLong, groupQuarterlyWide, groupMeta, groupSummary, groupMilestones] =
    await Promise.all([
      loadCsvFromCandidates(["country_quarterly_overview.csv"]),
      loadCsvFromCandidates(["group_quarterly_long.csv"]),
      loadCsvFromCandidates(["group_quarterly_rollout_enriched.csv", "group_quarterly_rollout.csv"]),
      loadCsvFromCandidates(["group_meta.csv"]),
      loadCsvFromCandidates(["group_summary.csv"]),
      loadCsvFromCandidates(["group_milestone_table.csv"]),
    ]);

  datasets.value = {
    countryQuarterly: countryQuarterly.rows,
    groupQuarterlyLong: groupQuarterlyLong.rows,
    groupQuarterlyWide: groupQuarterlyWide.rows,
    groupMeta: groupMeta.rows,
    groupSummary: groupSummary.rows,
    groupMilestones: groupMilestones.rows,
  };

  loadWarnings.value = [countryQuarterly, groupQuarterlyLong, groupQuarterlyWide, groupMeta, groupSummary, groupMilestones]
    .map((item) => item.error)
    .filter(Boolean);

  selectedQuarterIndex.value = Math.max(0, globalQuarters.value.length - 1);
});

watch(
  () => globalQuarters.value.length,
  (length) => {
    if (!length) {
      selectedQuarterIndex.value = 0;
      return;
    }
    if (selectedQuarterIndex.value > length - 1) {
      selectedQuarterIndex.value = length - 1;
    }
  }
);

const countryQuarterlyRows = computed(() =>
  datasets.value.countryQuarterly
    .map((row) => ({
      country: normalizeCountryName(pickField(row, ["country", "location"])),
      quarter: pickField(row, ["quarter"]),
      vacc_rollout_speed_avg: toNumber(pickField(row, ["vacc_rollout_speed_avg"])),
      vacc_rolling_6m_per_hundred: toNumber(pickField(row, ["vacc_rolling_6m_per_hundred"])),
      vacc_rolling_12m_per_hundred: toNumber(pickField(row, ["vacc_rolling_12m_per_hundred"])),
      cases_new_cases_pm_avg: toNumber(pickField(row, ["cases_new_cases_pm_avg"])),
      cases_new_cases_pm7_avg: toNumber(pickField(row, ["cases_new_cases_pm7_avg"])),
      cases_total_cases_pm_latest: toNumber(pickField(row, ["cases_total_cases_pm_latest"])),
    }))
    .filter((row) => row.country && row.quarter && !isAggregateLocation(row.country))
);

const globalQuarters = computed(() =>
  unique(
    countryQuarterlyRows.value
      .filter(
        (row) =>
          Number.isFinite(row.vacc_rollout_speed_avg) ||
          Number.isFinite(row.vacc_rolling_6m_per_hundred) ||
          Number.isFinite(row.vacc_rolling_12m_per_hundred)
      )
      .map((row) => row.quarter)
  )
    .filter(Boolean)
    .sort(sortQuarterKeys)
);

const selectedGlobalQuarter = computed(() => globalQuarters.value[selectedQuarterIndex.value] || "");

const countryRowsForQuarter = computed(() =>
  countryQuarterlyRows.value.filter((row) => row.quarter === selectedGlobalQuarter.value)
);

const vaccinationRows = computed(() =>
  countryRowsForQuarter.value.filter((row) => Number.isFinite(row[selectedVaccinationMetric.value]))
);

const caseRows = computed(() =>
  countryRowsForQuarter.value.filter((row) => Number.isFinite(row[selectedCaseMetric.value]))
);

const vaccinationRankedRows = computed(() => rankedRows(vaccinationRows.value, selectedVaccinationMetric.value).slice(0, 18));
const caseRankedRows = computed(() => rankedRows(caseRows.value, selectedCaseMetric.value).slice(0, 18));

const groupMetaOrder = computed(() => {
  const orderMap = {};
  datasets.value.groupMeta.forEach((row) => {
    const name = pickField(row, ["country", "group", "name"]);
    const order = toNumber(pickField(row, ["display_order", "order"]), Number.MAX_SAFE_INTEGER);
    if (name) {
      orderMap[name] = order;
    }
  });
  return orderMap;
});

const normalizedGroupLongRows = computed(() => {
  if (datasets.value.groupQuarterlyLong.length) {
    return datasets.value.groupQuarterlyLong
      .map((row) => ({
        group: pickField(row, ["country", "group"]),
        quarter: pickField(row, ["quarter"]),
        metric: pickField(row, ["metric"]),
        value: toNumber(pickField(row, ["value"])),
      }))
      .filter((row) => row.group && row.quarter && row.metric && Number.isFinite(row.value));
  }

  return datasets.value.groupQuarterlyWide
    .flatMap((row) =>
      ["rollout_speed", "first_dose_progress", "full_vaccination_progress"].map((metric) => ({
        group: pickField(row, ["country", "group"]),
        quarter: pickField(row, ["quarter"]),
        metric,
        value: toNumber(pickField(row, [metric])),
      }))
    )
    .filter((row) => row.group && row.quarter && row.metric && Number.isFinite(row.value));
});

const groupMetricMatrix = computed(() => {
  const groups = unique(normalizedGroupLongRows.value.map((row) => row.group)).sort((left, right) => {
    const leftOrder = groupMetaOrder.value[left] ?? Number.MAX_SAFE_INTEGER;
    const rightOrder = groupMetaOrder.value[right] ?? Number.MAX_SAFE_INTEGER;
    if (leftOrder !== rightOrder) {
      return leftOrder - rightOrder;
    }
    return left.localeCompare(right);
  });

  const quarters = unique(normalizedGroupLongRows.value.map((row) => row.quarter)).filter(Boolean).sort(sortQuarterKeys);
  const metricRows = normalizedGroupLongRows.value.filter((row) => row.metric === selectedGroupMetric.value);
  const valueMap = metricRows.reduce((map, row) => {
    map[`${row.group}__${row.quarter}`] = row.value;
    return map;
  }, {});

  return {
    groups,
    quarters,
    valueMap,
  };
});

const heatmapGridStyle = computed(() => ({
  gridTemplateColumns: `220px repeat(${Math.max(groupMetricMatrix.value.quarters.length, 1)}, minmax(96px, 1fr))`,
}));

const vaccinationLeaderCard = computed(() => {
  const leader = vaccinationRankedRows.value[0];
  return {
    title: leader?.country || "No data",
    value: leader ? `${selectedVaccinationMetricMeta.value.label}: ${selectedVaccinationMetricMeta.value.formatter(leader.value)}` : "No data in selected quarter",
  };
});

const caseLeaderCard = computed(() => {
  const leader = caseRankedRows.value[0];
  return {
    title: leader?.country || "No data",
    value: leader ? `${selectedCaseMetricMeta.value.label}: ${selectedCaseMetricMeta.value.formatter(leader.value)}` : "No data in selected quarter",
  };
});

const groupLeaderCard = computed(() => {
  const rows = normalizedGroupLongRows.value.filter(
    (row) => row.metric === selectedGroupMetric.value && row.quarter === selectedGlobalQuarter.value
  );
  const leader = [...rows].sort((left, right) => right.value - left.value)[0];
  return {
    title: leader?.group || "No data",
    value: leader ? `${selectedGroupMetricMeta.value.label}: ${selectedGroupMetricMeta.value.formatter(leader.value)}` : "No group row in selected quarter",
  };
});

const milestoneLeaderCard = computed(() => {
  const milestones = datasets.value.groupMilestones
    .map((row) => ({
      group: pickField(row, ["country", "group"]),
      metric: pickField(row, ["metric"]),
      threshold: toNumber(pickField(row, ["threshold"])),
      quarter: pickField(row, ["first_quarter_reached"]),
    }))
    .filter((row) => row.group && row.metric === "full_vaccination_progress" && row.threshold === 0.75 && row.quarter);

  const earliest = [...milestones].sort((left, right) => sortQuarterKeys(left.quarter, right.quarter))[0];
  return {
    title: earliest?.group || "No milestone",
    value: earliest ? `Earliest 75% full-vaccination milestone: ${earliest.quarter}` : "Milestone table unavailable",
  };
});

const vaccinationNarrative = computed(() => {
  const leader = vaccinationRankedRows.value[0];
  return (
    `Source: derived \`country_quarterly_overview.csv\`, built from \`data/cleaned_vaccinations_global.txt\`. ` +
    `This chart shows ${selectedVaccinationMetricMeta.value.description} in ${selectedGlobalQuarter.value}. ` +
    (leader ? `${leader.country} is the strongest visible signal in the selected quarter.` : `No stable vaccination signal is available for this quarter.`)
  );
});

const caseNarrative = computed(() => {
  const leader = caseRankedRows.value[0];
  return (
    `Source: derived \`country_quarterly_overview.csv\`, built from \`data/cleaned_cases_deaths.txt\`. ` +
    `This chart shows ${selectedCaseMetricMeta.value.description} in ${selectedGlobalQuarter.value}. ` +
    (leader ? `${leader.country} has the highest visible case burden in the selected quarter.` : `No stable case signal is available for this quarter.`)
  );
});

const groupNarrative = computed(() => {
  const firstQuarter = groupMetricMatrix.value.quarters[0];
  const latestQuarter = groupMetricMatrix.value.quarters[groupMetricMatrix.value.quarters.length - 1];
  return (
    `Source: \`group_quarterly_long.csv\`, with ordering from \`group_meta.csv\` and checks against \`group_summary.csv\` and \`group_milestone_table.csv\`. ` +
    `The heatmap shows quarter on the x-axis, group on the y-axis, and color for ${selectedGroupMetricMeta.value.label.toLowerCase()}. ` +
    `It is meant to show which groups moved earlier (${firstQuarter || "N/A"}) and which stayed strongest by the latest quarter (${latestQuarter || "N/A"}).`
  );
});

function normalizeCountryName(country) {
  return COUNTRY_ALIASES[country] || country;
}

function isAggregateLocation(country) {
  const aggregates = new Set([
    "World",
    "Africa",
    "Asia",
    "Europe",
    "North America",
    "South America",
    "Oceania",
    "European Union (27)",
    "European Union",
    "High-income countries",
    "Upper-middle-income countries",
    "Lower-middle-income countries",
    "Low-income countries",
    "International",
  ]);
  return aggregates.has(country) || /income/i.test(country);
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

function rankedRows(rows, field) {
  const validRows = rows.filter((row) => Number.isFinite(row[field]));
  const maxValue = Math.max(...validRows.map((row) => row[field]), 0);
  return [...validRows]
    .sort((left, right) => right[field] - left[field])
    .map((row) => ({
      ...row,
      value: row[field],
      width: maxValue > 0 ? (row[field] / maxValue) * 100 : 0,
    }));
}

function groupCellValue(group, quarter) {
  return groupMetricMatrix.value.valueMap[`${group}__${quarter}`];
}

function groupCellLabel(group, quarter) {
  const value = groupCellValue(group, quarter);
  if (!Number.isFinite(value)) {
    return "N/A";
  }
  return selectedGroupMetricMeta.value.formatter(value);
}

function groupCellTitle(group, quarter) {
  return `${group} | ${quarter} | ${selectedGroupMetricMeta.value.label}: ${groupCellLabel(group, quarter)}`;
}

function groupCellColor(group, quarter) {
  const value = groupCellValue(group, quarter);
  if (!Number.isFinite(value)) {
    return "rgba(242, 230, 211, 0.45)";
  }

  const metricValues = Object.values(groupMetricMatrix.value.valueMap).filter(Number.isFinite);
  const maxValue = Math.max(...metricValues, 0);
  const ratio = maxValue > 0 ? value / maxValue : 0;
  const lightness = 92 - ratio * 46;
  return `hsl(155 42% ${lightness}%)`;
}
</script>

<style scoped>
.overview-shell,
.overview-section {
  display: grid;
  gap: 1rem;
}

.overview-topbar {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: flex-start;
}

.overview-topbar h2 {
  margin: 0.15rem 0 0;
  font-size: 1.48rem;
}

.timeline-controls {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  align-items: flex-end;
  gap: 0.8rem;
}

.slider-stack {
  min-width: 260px;
}

.quarter-chip {
  min-width: 92px;
  justify-content: center;
}

.overview-cards {
  display: grid;
  gap: 0.9rem;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.overview-stat-card {
  padding: 1rem 1rem 0.95rem;
  border-radius: 18px;
  border: 1px solid rgba(31, 42, 31, 0.08);
  background: rgba(255, 255, 255, 0.58);
}

.overview-stat-card h3 {
  margin: 0.12rem 0 0.45rem;
  font-size: 1.12rem;
}

.overview-stat-card p:last-child {
  margin: 0;
  color: var(--muted);
  line-height: 1.55;
}

.viz-chart-intro {
  margin: 0 0 0.9rem;
  color: var(--muted);
  line-height: 1.58;
}

.ranking-stack {
  display: grid;
  gap: 0.75rem;
}

.ranking-row {
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr) 130px;
  gap: 0.8rem;
  align-items: center;
}

.ranking-meta {
  display: grid;
  gap: 0.16rem;
}

.ranking-meta span {
  color: var(--muted);
  font-size: 0.82rem;
}

.ranking-bar-track {
  height: 16px;
  border-radius: 999px;
  background: rgba(31, 42, 31, 0.09);
  overflow: hidden;
}

.ranking-bar {
  height: 100%;
  border-radius: 999px;
  transition: width 0.35s ease;
}

.ranking-bar-vaccination {
  background: linear-gradient(90deg, #6ea58a 0%, #1d6b57 100%);
}

.ranking-bar-case {
  background: linear-gradient(90deg, #efb07a 0%, #b85c38 100%);
}

.ranking-value {
  text-align: right;
  font-weight: 700;
  color: var(--ink);
}

.detailed-heat-cell {
  display: grid;
  place-items: center;
  min-height: 68px;
  padding: 0.4rem;
  text-align: center;
  border-radius: 10px;
  border: 1px solid rgba(31, 42, 31, 0.08);
}

.detailed-heat-cell span {
  font-size: 0.78rem;
  font-weight: 700;
  color: #17352f;
}

.empty-state {
  margin: 0;
  padding: 0.95rem 1rem;
  border-radius: 14px;
  background: rgba(242, 230, 211, 0.48);
  color: var(--muted);
}

.data-warning {
  margin: 0;
  color: var(--muted);
  font-size: 0.92rem;
}

@media (max-width: 1080px) {
  .overview-topbar {
    flex-direction: column;
  }

  .timeline-controls {
    width: 100%;
    justify-content: flex-start;
  }

  .overview-cards {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .ranking-row {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 680px) {
  .overview-cards {
    grid-template-columns: 1fr;
  }

  .slider-stack {
    min-width: 0;
    width: 100%;
  }
}
</style>
