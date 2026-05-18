<template>
  <section class="rollout-shell">
    <section class="panel-card section-card">
      <div class="section-heading">
        <div>
          <p class="viz-kicker">Section A</p>
          <h2>Cross-country rollout comparison</h2>
        </div>
      </div>

      <div class="card-grid">
        <article class="viz-card">
          <div class="viz-toolbar">
            <div>
              <p class="viz-kicker">A1</p>
              <h4>Daily First-dose Rollout Speed Aligned by Rollout Start</h4>
            </div>
            <label class="control-stack metric-control">
              <span>Rollout metric</span>
              <select v-model="selectedRolloutMetric">
                <option v-for="option in rolloutMetricOptions" :key="option.key" :value="option.key">
                  {{ option.label }}
                </option>
              </select>
            </label>
          </div>
          <p class="viz-chart-intro">
            Compare how quickly countries advanced after their own rollout starting point. Use the metric selector to switch
            between daily rollout speed, first-dose progress, and full vaccination completion.
          </p>
          <SvgLineChart
            v-if="rolloutLineSeries.length"
            title="Cross-country rollout comparison"
            :series="rolloutLineSeries"
            x-axis-label="Days since rollout start"
            :y-axis-label="selectedRolloutMetricMeta.axisLabel"
            :x-tick-formatter="formatRolloutDayTick"
            :y-tick-formatter="selectedRolloutMetricMeta.tickFormatter"
            :tooltip-formatter="formatRolloutTooltip"
            :playback-label-formatter="formatRolloutPlaybackLabel"
            :animate-key="selectedRolloutMetric"
            enable-playback
          />
          <p v-else class="empty-state">No aligned rollout data was found in `/public/analysis1`.</p>
        </article>

        <article class="viz-card">
          <div class="viz-toolbar">
            <div>
              <p class="viz-kicker">A2</p>
              <h4>Vaccination Progress at Day 30 / 60 / 80</h4>
            </div>
            <div class="segment-control">
              <button
                v-for="mode in progressModes"
                :key="mode.key"
                type="button"
                class="segment-button"
                :class="{ active: selectedProgressMode === mode.key }"
                @click="selectedProgressMode = mode.key"
              >
                {{ mode.label }}
              </button>
            </div>
          </div>
          <p class="viz-chart-intro">
            This grouped comparison focuses on progress milestones instead of raw speed, making it easier to see which
            countries translated early momentum into sustained dose completion by day 80.
          </p>
          <GroupedBarChart
            v-if="progressBarData.categories.length"
            title="Vaccination progress at day 30 60 and 80"
            :categories="progressBarData.categories"
            :series="progressBarData.series"
            x-axis-label="Country"
            y-axis-label="Coverage share"
            :y-tick-formatter="formatRatioTick"
            :tooltip-formatter="formatProgressTooltip"
          />
          <p v-else class="empty-state">No milestone summary table was found for day 30 / 60 / 80 comparisons.</p>
        </article>

        <article class="viz-card viz-card-wide">
          <div class="viz-toolbar">
            <div>
              <p class="viz-kicker">A3</p>
              <h4>Cross-country quarterly rollout heatmap</h4>
            </div>
          </div>
          <p class="viz-chart-intro">
            Each cell aggregates one quarter of rollout activity for one country. The matrix makes it easier to spot when
            acceleration concentrated in short bursts and when progress remained sustained across later quarters.
          </p>
          <CountryQuarterHeatmap
            v-if="rolloutHeatmap.quarters.length && rolloutHeatmap.countries.length"
            :countries="rolloutHeatmap.countries"
            :quarters="rolloutHeatmap.quarters"
            :cells="rolloutHeatmap.cells"
            :metric-label="rolloutHeatmap.metricLabel"
            :value-formatter="rolloutHeatmap.valueFormatter"
          />
          <p v-else class="empty-state">Quarterly heatmap data could not be assembled from the aligned rollout table.</p>
        </article>
      </div>

      <p class="section-note body-note">
        The rollout comparison highlights substantial cross-country differences in early vaccine expansion. Some countries
        advanced rapidly within the first 30 to 80 days, while others showed a slower but steadier pace. The contrast
        between first-dose expansion and full vaccination completion also suggests that rapid initial coverage did not
        always translate into equally fast completion.
      </p>

      <div class="findings-grid">
        <article v-for="(item, index) in rolloutFindings" :key="`rollout-${index}`" class="finding-card">
          <p class="viz-kicker">Finding {{ index + 1 }}</p>
          <p>{{ item }}</p>
        </article>
      </div>
    </section>

    <GroupRolloutAnalytics />

    <CurveFitAnalysis />

    <section class="panel-card section-card">
      <div class="section-heading">
        <div>
          <p class="viz-kicker">Section B</p>
          <h2>Age-priority analysis</h2>
        </div>
      </div>

      <div class="focus-switcher">
        <span class="focus-label">View mode</span>
        <div class="segment-control">
          <button
            type="button"
            class="segment-button"
            :class="{ active: selectedAgeCountry === 'All countries' }"
            @click="selectedAgeCountry = 'All countries'"
          >
            All countries
          </button>
          <button
            v-for="country in ageCountries"
            :key="country"
            type="button"
            class="segment-button"
            :class="{ active: selectedAgeCountry === country }"
            @click="selectedAgeCountry = country"
          >
            {{ country }}
          </button>
        </div>
      </div>

      <div class="age-focus-summary">
        <div class="focus-summary-card">
          <p class="viz-kicker">Current lens</p>
          <h3>{{ selectedAgeCountry }}</h3>
          <p>{{ ageFocusNarrative }}</p>
        </div>
        <div class="focus-summary-card">
          <p class="viz-kicker">Why this helps</p>
          <p>
            Single-country focus removes the spaghetti effect. Use `All countries` only when you want cross-country contrast
            after understanding each rollout story on its own.
          </p>
        </div>
      </div>

      <div class="card-grid">
        <article class="viz-card">
          <div class="viz-toolbar">
            <div>
              <p class="viz-kicker">B1</p>
              <h4>First-dose Coverage: 80+ vs 18–24 Across Selected Countries</h4>
            </div>
          </div>
          <p class="viz-chart-intro">
            Each country contributes two traces, allowing you to compare whether older adults were moved ahead of younger
            adults and how long that lead persisted as rollout capacity expanded.
          </p>
          <SvgLineChart
            v-if="filteredAgeCoverageSeries.length"
            title="First-dose coverage 80+ vs 18-24"
            :series="filteredAgeCoverageSeries"
            x-axis-label="Date"
            y-axis-label="People vaccinated per hundred"
            :x-tick-formatter="formatDateTick"
            :y-tick-formatter="formatPercentTick"
            :tooltip-formatter="formatAgeCoverageTooltip"
            :playback-label-formatter="formatDatePlaybackLabel"
            :animate-key="`age-coverage-${selectedAgeCountry}`"
            enable-playback
          />
          <p v-else class="empty-state">Age-stratified first-dose coverage data is unavailable.</p>
          <p class="chart-note">
            Some age-specific coverage values may exceed 100 due to denominator estimation and reporting adjustments in the
            source data.
          </p>
        </article>

        <article class="viz-card">
          <div class="viz-toolbar">
            <div>
              <p class="viz-kicker">B2</p>
              <h4>Age Priority Gap Over Time (80+ minus 18–24)</h4>
            </div>
          </div>
          <p class="viz-chart-intro">
            The zero reference line marks the point where coverage between the two groups is equal. Positive values indicate
            an elderly lead, while negative values show younger adults catching up or moving ahead.
          </p>
          <SvgLineChart
            v-if="filteredGapSeries.length"
            title="Age priority gap over time"
            :series="filteredGapSeries"
            x-axis-label="Date"
            y-axis-label="Coverage gap (percentage points)"
            :x-tick-formatter="formatDateTick"
            :y-tick-formatter="formatGapTick"
            :tooltip-formatter="formatGapTooltip"
            :playback-label-formatter="formatDatePlaybackLabel"
            :animate-key="`gap-series-${selectedAgeCountry}`"
            enable-playback
            show-zero-line
          />
          <p v-else class="empty-state">Gap-tracking data is unavailable for the selected countries.</p>
        </article>

        <article class="viz-card viz-card-wide">
          <div class="viz-toolbar">
            <div>
              <p class="viz-kicker">B3</p>
              <h4>Full Vaccination Coverage by Age Group</h4>
            </div>
          </div>
          <p class="viz-chart-intro">
            This snapshot compares age-specific full vaccination coverage at the latest common reporting date shared across
            the selected age-structured countries.
          </p>
          <GroupedBarChart
            v-if="fullVaccinationSnapshot.categories.length"
            title="Full vaccination coverage by age group"
            :categories="fullVaccinationSnapshot.categories"
            :series="fullVaccinationSnapshot.series"
            x-axis-label="Age group"
            y-axis-label="People fully vaccinated per hundred"
            :y-tick-formatter="formatPercentTick"
            :tooltip-formatter="formatAgeBarTooltip"
          />
          <p class="snapshot-caption" v-if="fullVaccinationSnapshot.snapshotLabel">
            Snapshot date: {{ fullVaccinationSnapshot.snapshotLabel }}
          </p>
          <p v-else class="empty-state">No common age-group snapshot could be assembled from the available files.</p>
        </article>
      </div>

      <div class="supplement-card">
        <details>
          <summary>
            <span>
              <strong>Japan: First-dose Coverage by Age Group</strong>
              <small>Supplementary case view from `japan_age_df.csv`</small>
            </span>
          </summary>
          <div class="supplement-body">
            <p class="viz-chart-intro supplement-note">
              Japan is shown separately here because it offers a denser age breakdown than the three-country comparison
              above, helping illustrate how age-specific rollout broadened after the earliest elderly-first phase.
            </p>
            <SvgLineChart
              v-if="japanSeries.length"
              title="Japan first dose coverage by age group"
              :series="japanSeries"
              x-axis-label="Date"
              y-axis-label="People vaccinated per hundred"
              :x-tick-formatter="formatDateTick"
              :y-tick-formatter="formatPercentTick"
              :tooltip-formatter="formatJapanTooltip"
              :playback-label-formatter="formatDatePlaybackLabel"
              chart-tone="japan"
              animate-key="japan-series"
              enable-playback
            />
            <p v-else class="empty-state">Japan supplementary age data is unavailable.</p>
            <p class="chart-note">
              Some age-specific coverage values may exceed 100 due to denominator estimation and reporting adjustments in the
              source data.
            </p>
          </div>
        </details>
      </div>

      <p class="section-note body-note">
        The age-group analysis shows that vaccination rollout was not uniform across population segments. In several
        countries, older groups achieved high coverage earlier than younger adults, indicating a clear priority strategy.
        The age-priority gap also changed over time, revealing whether the early elderly advantage narrowed or remained
        persistent as the campaign matured.
      </p>

      <div class="findings-grid">
        <article v-for="(item, index) in ageFindings" :key="`age-${index}`" class="finding-card">
          <p class="viz-kicker">Finding {{ index + 1 }}</p>
          <p>{{ item }}</p>
        </article>
      </div>
    </section>

    <section class="panel-card section-card">
      <div class="section-heading">
        <div>
          <p class="viz-kicker">Section C</p>
          <h2>Key findings</h2>
        </div>
      </div>

      <div class="findings-grid key-grid">
        <article v-for="(item, index) in keyFindings" :key="`key-${index}`" class="finding-card">
          <p class="viz-kicker">Key finding {{ index + 1 }}</p>
          <p>{{ item }}</p>
        </article>
      </div>
    </section>

    <p v-if="loadWarnings.length" class="data-warning">Data notes: {{ loadWarnings.join(" | ") }}</p>
  </section>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import CountryQuarterHeatmap from "./CountryQuarterHeatmap.vue";
import CurveFitAnalysis from "./CurveFitAnalysis.vue";
import GroupRolloutAnalytics from "./GroupRolloutAnalytics.vue";
import GroupedBarChart from "./GroupedBarChart.vue";
import SvgLineChart from "./SvgLineChart.vue";
import {
  formatDateLabel,
  formatMonthLabel,
  formatPercent,
  formatSignedPercent,
  groupBy,
  loadCsvFromCandidates,
  parseDateValue,
  pickField,
  toNumber,
  unique
} from "../../utils/csv";

const palette = ["#1d6b57", "#b85c38", "#4f7d6b", "#c47b2f", "#506f97", "#875167", "#465c3f"];
const agePalette = {
  old: "#1d6b57",
  young: "#d38a46"
};
const japanPalette = ["#1f5f8b", "#8d4f20", "#1f6a58", "#7f2f48", "#5f4f9d", "#8a6a1d", "#375d3f"];

const datasets = ref({
  aligned: [],
  feature: [],
  result: [],
  startDates: [],
  ageMain: [],
  gap: [],
  gapSnapshot: [],
  japanAge: []
});
const loadWarnings = ref([]);

const rolloutMetricOptions = [
  {
    key: "daily_people_vaccinated_smoothed_per_hundred",
    label: "Daily rollout speed",
    axisLabel: "Daily first-dose rollout per hundred",
    tickFormatter: (value) => `${value.toFixed(2)}`
  },
  {
    key: "vaccinated_progress_ratio",
    label: "First-dose progress",
    axisLabel: "First-dose progress ratio",
    tickFormatter: (value) => `${(value * 100).toFixed(0)}%`
  },
  {
    key: "fully_vaccinated_progress_ratio",
    label: "Full vaccination progress",
    axisLabel: "Full vaccination progress ratio",
    tickFormatter: (value) => `${(value * 100).toFixed(0)}%`
  }
];

const progressModes = [
  { key: "firstDose", label: "First-dose" },
  { key: "fullDose", label: "Full vaccination" }
];

const selectedRolloutMetric = ref("daily_people_vaccinated_smoothed_per_hundred");
const selectedProgressMode = ref("firstDose");
const selectedAgeCountry = ref("All countries");

const selectedRolloutMetricMeta = computed(
  () => rolloutMetricOptions.find((option) => option.key === selectedRolloutMetric.value) || rolloutMetricOptions[0]
);

onMounted(async () => {
  const [aligned, feature, result, startDates, ageMain, gap, gapSnapshot, japanAge] = await Promise.all([
    loadCsvFromCandidates(["aligned_df.csv"]),
    loadCsvFromCandidates(["feature_df.csv"]),
    loadCsvFromCandidates(["result_table.csv", "vaccination_trend_result_table.csv"]),
    loadCsvFromCandidates(["start_dates_df.csv", "vaccination_rollout_start_dates.csv"]),
    loadCsvFromCandidates(["age_main_df.csv"]),
    loadCsvFromCandidates(["gap_df.csv"]),
    loadCsvFromCandidates(["gap_snapshot_df.csv"]),
    loadCsvFromCandidates(["japan_age_df.csv"])
  ]);

  datasets.value = {
    aligned: aligned.rows,
    feature: feature.rows,
    result: result.rows,
    startDates: startDates.rows,
    ageMain: ageMain.rows,
    gap: gap.rows,
    gapSnapshot: gapSnapshot.rows,
    japanAge: japanAge.rows
  };

  loadWarnings.value = [aligned, feature, result, startDates, ageMain, gap, gapSnapshot, japanAge]
    .map((item) => item.error)
    .filter(Boolean);
});

const rolloutCountries = computed(() =>
  unique(datasets.value.aligned.map((row) => pickField(row, ["country"])).filter(Boolean))
);

const rolloutLineSeries = computed(() =>
  rolloutCountries.value.map((country, index) => {
    const points = datasets.value.aligned
      .filter((row) => pickField(row, ["country"]) === country)
      .map((row) => {
        const x = toNumber(pickField(row, ["rollout_day", "rolloutday"]));
        const y = toNumber(pickField(row, [selectedRolloutMetric.value]));
        const date = pickField(row, ["date"]);
        return {
          x,
          y,
          label: `Day ${x}`,
          meta: date ? formatDateLabel(date) : ""
        };
      })
      .filter((point) => Number.isFinite(point.x) && Number.isFinite(point.y))
      .sort((left, right) => left.x - right.x);

    return {
      key: country,
      label: country,
      color: palette[index % palette.length],
      points
    };
  })
);

const orderedRolloutCountries = computed(() => {
  const startMap = datasets.value.startDates.reduce((map, row) => {
    const country = pickField(row, ["country"]);
    const date = pickField(row, ["rollout_start_date", "date", "rolloutstartdate"]);
    const timestamp = parseDateValue(date);
    if (country && Number.isFinite(timestamp)) {
      map[country] = timestamp;
    }
    return map;
  }, {});

  return [...rolloutCountries.value].sort((left, right) => {
    const leftStart = startMap[left] ?? Number.MAX_SAFE_INTEGER;
    const rightStart = startMap[right] ?? Number.MAX_SAFE_INTEGER;
    if (leftStart !== rightStart) {
      return leftStart - rightStart;
    }
    return left.localeCompare(right);
  });
});

const rolloutHeatmap = computed(() => {
  const metricKey = selectedRolloutMetric.value;
  const metricLabel = selectedRolloutMetricMeta.value.label;
  const quarterMap = {};

  datasets.value.aligned.forEach((row) => {
    const country = pickField(row, ["country"]);
    const date = pickField(row, ["date"]);
    const timestamp = parseDateValue(date);
    const value = toNumber(pickField(row, [metricKey]));

    if (!country || !Number.isFinite(timestamp) || !Number.isFinite(value)) {
      return;
    }

    const quarter = getQuarterKey(timestamp);
    const bucketKey = `${country}__${quarter}`;

    if (!quarterMap[bucketKey]) {
      quarterMap[bucketKey] = {
        country,
        quarter,
        values: [],
        latestTimestamp: timestamp,
        latestValue: value
      };
    }

    quarterMap[bucketKey].values.push(value);
    if (timestamp >= quarterMap[bucketKey].latestTimestamp) {
      quarterMap[bucketKey].latestTimestamp = timestamp;
      quarterMap[bucketKey].latestValue = value;
    }
  });

  const countries = orderedRolloutCountries.value.filter((country) =>
    Object.values(quarterMap).some((entry) => entry.country === country)
  );
  const quarterCounts = Object.values(quarterMap).reduce((map, entry) => {
    map[entry.quarter] = (map[entry.quarter] || 0) + 1;
    return map;
  }, {});
  const quarterList = unique(Object.values(quarterMap).map((entry) => entry.quarter))
    .filter((quarter) => quarterCounts[quarter] === countries.length)
    .sort(sortQuarterKeys);

  const isSpeedMetric = metricKey === "daily_people_vaccinated_smoothed_per_hundred";
  const valueFormatter = (value) =>
    isSpeedMetric ? `${Number(value).toFixed(3)} / 100` : `${(Number(value) * 100).toFixed(1)}%`;

  const cells = [];

  countries.forEach((country) => {
    quarterList.forEach((quarter) => {
      const bucket = quarterMap[`${country}__${quarter}`];
      if (!bucket) {
        return;
      }

      cells.push({
        country,
        quarter,
        value: isSpeedMetric ? average(bucket.values) : bucket.latestValue
      });
    });
  });

  return {
    countries,
    quarters: quarterList,
    cells,
    metricLabel: isSpeedMetric ? `${metricLabel} (quarter average)` : `${metricLabel} (quarter-end level)`,
    valueFormatter
  };
});

const progressSummaryRows = computed(() => {
  const featureRows = datasets.value.feature.length ? datasets.value.feature : datasets.value.result;
  return featureRows
    .map((row) => ({
      country: pickField(row, ["country"]),
      first30: toNumber(pickField(row, ["vaccinated_day_30_ratio"])) ?? 0,
      first60: toNumber(pickField(row, ["vaccinated_day_60_ratio"])) ?? 0,
      first80: toNumber(pickField(row, ["vaccinated_day_80_ratio"])) ?? 0,
      full30: toNumber(pickField(row, ["fully_vaccinated_day_30_ratio"])) ?? 0,
      full60: toNumber(pickField(row, ["fully_vaccinated_day_60_ratio"])) ?? 0,
      full80: toNumber(pickField(row, ["fully_vaccinated_day_80_ratio"])) ?? 0
    }))
    .filter((row) => row.country);
});

const progressBarData = computed(() => {
  const rows = progressSummaryRows.value;
  const isFirstDose = selectedProgressMode.value === "firstDose";

  return {
    categories: rows.map((row) => row.country),
    series: [
      {
        key: "day30",
        label: "Day 30",
        color: "#c47b2f",
        values: rows.map((row) => (isFirstDose ? row.first30 : row.full30))
      },
      {
        key: "day60",
        label: "Day 60",
        color: "#4f7d6b",
        values: rows.map((row) => (isFirstDose ? row.first60 : row.full60))
      },
      {
        key: "day80",
        label: "Day 80",
        color: "#1d6b57",
        values: rows.map((row) => (isFirstDose ? row.first80 : row.full80))
      }
    ]
  };
});

const ageCountries = computed(() =>
  unique(datasets.value.gap.map((row) => pickField(row, ["country"])).filter(Boolean))
);

watch(
  ageCountries,
  (countries) => {
    if (!countries.length) {
      selectedAgeCountry.value = "All countries";
      return;
    }
    if (selectedAgeCountry.value !== "All countries" && !countries.includes(selectedAgeCountry.value)) {
      selectedAgeCountry.value = "All countries";
    }
  },
  { immediate: true }
);

const ageCoverageSeries = computed(() => {
  const filtered = datasets.value.ageMain.filter((row) => {
    const ageGroup = pickField(row, ["age_group", "agegroup"]);
    const country = pickField(row, ["country"]);
    return ageCountries.value.includes(country) && ["80+", "18-24"].includes(ageGroup);
  });

  const grouped = groupBy(filtered, (row) => `${pickField(row, ["country"])}__${pickField(row, ["age_group", "agegroup"])}`);

  return Object.entries(grouped).map(([key, rows]) => {
    const [country, ageGroup] = key.split("__");
    const color = ageGroup === "80+" ? agePalette.old : agePalette.young;
    const points = rows
      .map((row) => {
        const date = pickField(row, ["date"]);
        return {
          x: parseDateValue(date),
          y: toNumber(pickField(row, ["people_vaccinated_per_hundred", "peoplevaccinatedperhundred"])),
          label: formatDateLabel(date),
          meta: `${country} · ${ageGroup}`
        };
      })
      .filter((point) => Number.isFinite(point.x) && Number.isFinite(point.y))
      .sort((left, right) => left.x - right.x);

    return {
      key,
      label: `${country} · ${ageGroup}`,
      country,
      color,
      points
    };
  });
});

const gapSeries = computed(() =>
  ageCountries.value.map((country, index) => {
    const points = datasets.value.gap
      .filter((row) => pickField(row, ["country"]) === country)
      .map((row) => {
        const date = pickField(row, ["date"]);
        return {
          x: parseDateValue(date),
          y: toNumber(pickField(row, ["age_priority_gap", "priority_gap_80_vs_18_24"])),
          label: formatDateLabel(date)
        };
      })
      .filter((point) => Number.isFinite(point.x) && Number.isFinite(point.y))
      .sort((left, right) => left.x - right.x);

    return {
      key: country,
      label: country,
      country,
      color: palette[index % palette.length],
      points
    };
  })
);

const filteredAgeCoverageSeries = computed(() =>
  selectedAgeCountry.value === "All countries"
    ? ageCoverageSeries.value
    : ageCoverageSeries.value.filter((series) => series.country === selectedAgeCountry.value)
);

const filteredGapSeries = computed(() =>
  selectedAgeCountry.value === "All countries"
    ? gapSeries.value
    : gapSeries.value.filter((series) => series.country === selectedAgeCountry.value)
);

const ageFocusNarrative = computed(() => {
  if (selectedAgeCountry.value === "All countries") {
    return "Cross-country mode is useful for contrast, but it is intentionally denser. Use it after reading each country separately so the animation works as comparison rather than clutter.";
  }

  const coverage = ageCoverageSeries.value.filter((series) => series.country === selectedAgeCountry.value);
  const older = coverage.find((series) => series.label.includes("80+"));
  const younger = coverage.find((series) => series.label.includes("18-24"));
  const olderPeak = older?.points.at(-1)?.y ?? null;
  const youngerPeak = younger?.points.at(-1)?.y ?? null;

  if (Number.isFinite(olderPeak) && Number.isFinite(youngerPeak)) {
    const gap = olderPeak - youngerPeak;
    return `${selectedAgeCountry.value} ends with ${formatPercent(olderPeak, 1)} for 80+ and ${formatPercent(youngerPeak, 1)} for 18–24, a latest visible gap of ${formatSignedPercent(gap, 1)}.`;
  }

  return `${selectedAgeCountry.value} is in focus so the moving state and elderly-versus-young contrast can be read without cross-country overlap.`;
});

const fullVaccinationSnapshot = computed(() => {
  const countries = unique(datasets.value.ageMain.map((row) => pickField(row, ["country"])).filter(Boolean));
  const datesByCountry = countries.reduce((map, country) => {
    map[country] = unique(
      datasets.value.ageMain
        .filter((row) => pickField(row, ["country"]) === country)
        .map((row) => pickField(row, ["date"]))
        .filter(Boolean)
    );
    return map;
  }, {});

  const commonDates = Object.values(datesByCountry).reduce((shared, dates, index) => {
    if (index === 0) {
      return dates;
    }
    return shared.filter((date) => dates.includes(date));
  }, []);

  const latestCommonDate = commonDates
    .map((date) => ({ date, timestamp: parseDateValue(date) }))
    .filter((item) => Number.isFinite(item.timestamp))
    .sort((left, right) => right.timestamp - left.timestamp)[0]?.date;

  if (!latestCommonDate) {
    return { categories: [], series: [], snapshotLabel: "" };
  }

  const rows = datasets.value.ageMain.filter((row) => pickField(row, ["date"]) === latestCommonDate);
  const categories = unique(rows.map((row) => pickField(row, ["age_group", "agegroup"]))).sort(sortAgeGroups);
  const series = countries.map((country, index) => ({
    key: country,
    label: country,
    color: palette[index % palette.length],
    values: categories.map((ageGroup) => {
      const match = rows.find(
        (row) => pickField(row, ["country"]) === country && pickField(row, ["age_group", "agegroup"]) === ageGroup
      );
      return toNumber(pickField(match, ["people_fully_vaccinated_per_hundred", "peoplefullyvaccinatedperhundred"]));
    })
  }));

  return {
    categories,
    series,
    snapshotLabel: formatDateLabel(latestCommonDate)
  };
});

const japanSeries = computed(() => {
  const grouped = groupBy(datasets.value.japanAge, (row) => pickField(row, ["age_group", "agegroup"]));
  return Object.entries(grouped)
    .map(([ageGroup, rows], index) => ({
      key: ageGroup,
      label: ageGroup,
      color: japanPalette[index % japanPalette.length],
      lineWidth: 4.4,
      activeLineWidth: 6.2,
      pointRadius: 5,
      activePointRadius: 6.6,
      opacity: 0.98,
      mutedOpacity: 0.12,
      points: rows
        .map((row) => {
          const date = pickField(row, ["date"]);
          return {
            x: parseDateValue(date),
            y: toNumber(pickField(row, ["people_vaccinated_per_hundred", "peoplevaccinatedperhundred"])),
            label: formatDateLabel(date),
            meta: ageGroup
          };
        })
        .filter((point) => Number.isFinite(point.x) && Number.isFinite(point.y))
        .sort((left, right) => left.x - right.x)
    }))
    .sort((left, right) => sortAgeGroups(left.label, right.label));
});

const rolloutFindings = computed(() => {
  const starts = datasets.value.startDates
    .map((row) => ({
      country: pickField(row, ["country"]),
      date: pickField(row, ["rollout_start_date", "date", "rolloutstartdate"])
    }))
    .filter((item) => item.country && item.date)
    .sort((left, right) => parseDateValue(left.date) - parseDateValue(right.date));

  const milestones = progressSummaryRows.value;
  const fastestDay30 = [...milestones].sort((left, right) => right.first30 - left.first30)[0];
  const strongestDay80 = [...milestones].sort((left, right) => right.full80 - left.full80)[0];
  const earliest = starts[0];
  const latest = starts[starts.length - 1];

  return [
    earliest && latest
      ? `Rollout start dates in this panel span from ${earliest.country} on ${formatDateLabel(earliest.date)} to ${latest.country} on ${formatDateLabel(latest.date)}, reinforcing that countries entered the acceleration phase on different calendars.`
      : "Early rollout speed varied strongly across countries, especially within the first 30 to 80 days.",
    fastestDay30
      ? `${fastestDay30.country} reached the strongest first-dose position by day 30 at ${formatPercent(fastestDay30.first30 * 100, 1)}, showing how uneven the first expansion wave was across countries.`
      : "First-dose expansion and full vaccination completion did not always progress at the same pace.",
    strongestDay80
      ? `${strongestDay80.country} posted the highest full-vaccination progress by day 80 at ${formatPercent(strongestDay80.full80 * 100, 1)}, which is not always the same country that led the earliest first-dose sprint.`
      : "Some countries showed much stronger early acceleration, while others followed a slower but more gradual trajectory."
  ];
});

const ageFindings = computed(() => {
  const latestGaps = datasets.value.gapSnapshot
    .map((row) => ({
      country: pickField(row, ["country"]),
      gap: toNumber(pickField(row, ["priority_gap_80_vs_18_24", "age_priority_gap"]))
    }))
    .filter((item) => item.country && Number.isFinite(item.gap));

  const largestPositive = [...latestGaps].sort((left, right) => right.gap - left.gap)[0];
  const largestNegative = [...latestGaps].sort((left, right) => left.gap - right.gap)[0];
  const averagePeakGap = average(
    ageCountries.value.map((country) => {
      const values = datasets.value.gap
        .filter((row) => pickField(row, ["country"]) === country)
        .map((row) => toNumber(pickField(row, ["age_priority_gap"])))
        .filter((value) => Number.isFinite(value));
      return values.length ? Math.max(...values) : null;
    })
  );

  return [
    Number.isFinite(averagePeakGap)
      ? `Across the age-structured countries, the average peak elderly advantage reached about ${formatPercent(averagePeakGap, 1)}, which is consistent with an explicit older-first rollout strategy.`
      : "Older age groups were generally prioritized earlier than younger groups in the selected age-structured countries.",
    largestPositive
      ? `${largestPositive.country} retained the strongest latest 80+ lead at ${formatSignedPercent(largestPositive.gap, 1)}, suggesting that the early elderly advantage remained material even at later stages.`
      : "The elderly advantage was strongest in the early rollout phase and then either narrowed or stabilized over time.",
    largestNegative
      ? `${largestNegative.country} shows the clearest later reversal at ${formatSignedPercent(largestNegative.gap, 1)}, indicating that some countries eventually shifted toward broad younger-adult catch-up.`
      : "Age-priority patterns differed across countries, indicating different rollout strategies and public-health priorities."
  ];
});

const keyFindings = [
  "Early rollout speed varied strongly across countries, especially within the first 30 to 80 days.",
  "First-dose expansion and full vaccination completion did not always progress at the same pace.",
  "Older age groups were generally prioritized earlier than younger groups in the selected age-structured countries.",
  "Age-priority patterns differed across countries, suggesting different public-health rollout strategies."
];

function formatRolloutDayTick(value) {
  return `Day ${Math.round(value)}`;
}

function formatRolloutTooltip(series, point) {
  const metric = selectedRolloutMetricMeta.value.label;
  const value =
    selectedRolloutMetric.value === "daily_people_vaccinated_smoothed_per_hundred"
      ? `${point.y.toFixed(3)} per hundred`
      : formatPercent(point.y * 100, 1);

  return {
    title: series.label,
    lines: [
      `Metric: ${metric}`,
      `Aligned day: ${point.label}`,
      point.meta ? `Source date: ${point.meta}` : null,
      `Value: ${value}`
    ].filter(Boolean)
  };
}

function formatRatioTick(value) {
  return `${(value * 100).toFixed(0)}%`;
}

function formatPercentTick(value) {
  return `${value.toFixed(0)}%`;
}

function formatGapTick(value) {
  return `${value.toFixed(0)} pts`;
}

function formatDateTick(value) {
  return formatMonthLabel(value);
}

function formatProgressTooltip(category, bar) {
  return {
    title: `${category} · ${bar.label}`,
    lines: [
      `${selectedProgressMode.value === "firstDose" ? "First-dose" : "Full vaccination"} progress`,
      `Value: ${formatPercent(bar.value * 100, 1)}`
    ]
  };
}

function formatAgeCoverageTooltip(series, point) {
  return {
    title: series.label,
    lines: [
      `Country / age group: ${series.label}`,
      `Date: ${point.label}`,
      `First-dose coverage: ${formatPercent(point.y, 1)}`
    ]
  };
}

function formatGapTooltip(series, point) {
  return {
    title: series.label,
    lines: [`Country: ${series.label}`, `Date: ${point.label}`, `Gap: ${formatSignedPercent(point.y, 1)}`]
  };
}

function formatAgeBarTooltip(category, bar) {
  return {
    title: `${bar.label} · ${category}`,
    lines: [`Full vaccination: ${formatPercent(bar.value, 1)}`]
  };
}

function formatJapanTooltip(series, point) {
  return {
    title: `Japan · ${series.label}`,
    lines: [`Age group: ${series.label}`, `Date: ${point.label}`, `First-dose coverage: ${formatPercent(point.y, 1)}`]
  };
}

function formatRolloutPlaybackLabel(value) {
  return `Through day ${Math.round(value)}`;
}

function formatDatePlaybackLabel(value) {
  return formatMonthLabel(value);
}

function getQuarterKey(timestamp) {
  const date = new Date(timestamp);
  const quarter = Math.floor(date.getUTCMonth() / 3) + 1;
  return `${date.getUTCFullYear()}-Q${quarter}`;
}

function sortQuarterKeys(left, right) {
  const [leftYear, leftQuarter] = left.split("-Q").map(Number);
  const [rightYear, rightQuarter] = right.split("-Q").map(Number);
  if (leftYear !== rightYear) {
    return leftYear - rightYear;
  }
  return leftQuarter - rightQuarter;
}

function sortAgeGroups(left, right) {
  const order = ["0-17", "0-5", "6-11", "12-17", "18-24", "25-49", "50-59", "60-69", "70-79", "80+"];
  return order.indexOf(left) - order.indexOf(right);
}

function average(values) {
  const filtered = values.filter((value) => Number.isFinite(value));
  return filtered.length ? filtered.reduce((sum, value) => sum + value, 0) / filtered.length : null;
}
</script>

<style scoped>
.rollout-shell {
  display: grid;
  gap: 1rem;
}

.section-card {
  display: grid;
  gap: 1rem;
}

.section-heading {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: flex-start;
}

.section-heading h2 {
  margin: 0.15rem 0 0;
  font-size: 1.42rem;
}

.metric-control {
  min-width: 220px;
}

.metric-control select {
  border: 1px solid rgba(31, 42, 31, 0.14);
  border-radius: 12px;
  background: rgba(255, 250, 242, 0.98);
  color: var(--ink);
  padding: 0.62rem 0.75rem;
  font: inherit;
}

.card-grid {
  display: grid;
  gap: 1rem;
}

.two-up {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.viz-chart-intro {
  margin: 0 0 0.9rem;
  color: var(--muted);
  line-height: 1.58;
}

.body-note {
  margin-top: -0.1rem;
  line-height: 1.62;
}

.focus-switcher {
  display: grid;
  gap: 0.5rem;
}

.focus-label {
  color: var(--muted);
  font-size: 0.82rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.age-focus-summary {
  display: grid;
  gap: 0.9rem;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.focus-summary-card {
  padding: 0.95rem 1rem;
  border-radius: 18px;
  background: rgba(242, 230, 211, 0.46);
  border: 1px solid rgba(31, 42, 31, 0.08);
}

.focus-summary-card h3 {
  margin: 0.15rem 0 0.45rem;
  font-size: 1.18rem;
}

.focus-summary-card p:last-child {
  margin: 0;
  color: var(--muted);
  line-height: 1.56;
}

.findings-grid {
  display: grid;
  gap: 0.9rem;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
}

.finding-card {
  padding: 1rem 1rem 0.95rem;
  border-radius: 18px;
  background: rgba(242, 230, 211, 0.52);
  border: 1px solid rgba(31, 42, 31, 0.08);
}

.finding-card p:last-child {
  margin: 0.2rem 0 0;
  line-height: 1.58;
  color: var(--ink);
}

.supplement-card {
  border-radius: 18px;
  border: 1px solid rgba(31, 42, 31, 0.08);
  background: rgba(255, 255, 255, 0.56);
}

.supplement-card details {
  padding: 0.9rem 1rem 1rem;
}

.supplement-card summary {
  cursor: pointer;
  list-style: none;
}

.supplement-card summary::-webkit-details-marker {
  display: none;
}

.supplement-card summary span {
  display: grid;
  gap: 0.2rem;
}

.supplement-card summary strong {
  font-size: 1rem;
}

.supplement-card summary small {
  color: var(--muted);
}

.supplement-body {
  margin-top: 0.85rem;
}

.supplement-note {
  margin-bottom: 0.8rem;
}

.snapshot-caption {
  margin: 0.75rem 0 0;
  color: var(--muted);
  font-size: 0.94rem;
}

.chart-note {
  margin: 0.75rem 0 0;
  color: var(--muted);
  font-size: 0.9rem;
  line-height: 1.5;
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

.key-grid .finding-card {
  background: rgba(255, 250, 242, 0.72);
}

@media (max-width: 980px) {
  .age-focus-summary {
    grid-template-columns: 1fr;
  }

  .section-heading {
    flex-direction: column;
  }

  .metric-control {
    width: 100%;
    min-width: 0;
  }
}
</style>
