<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import Plotly from "plotly.js-dist-min";

const COUNTRY_METADATA_SOURCES = [
  "/maps/countries.json",
  "https://raw.githubusercontent.com/mledoze/countries/master/countries.json"
];
const CLIP_QUANTILE = 0.995;
const MODEL_OPTIONS = [
  {
    id: "neural",
    label: "Neural (GNN-RNN)",
    endpoint: "/api/v1/infections/neural-prediction"
  },
  {
    id: "traditional_onnx",
    label: "ML_model ONNX",
    endpoint: "/api/v1/infections/traditional-onnx-forecast"
  }
];

const COUNTRY_ALIASES = {
  "United States": "United States of America",
  "Democratic Republic of Congo": "Dem. Rep. Congo",
  "North Korea": "Dem. Rep. Korea",
  "South Korea": "Korea",
  Czechia: "Czech Republic",
  "Bosnia and Herzegovina": "Bosnia and Herz.",
  "Dominican Republic": "Dominican Rep.",
  "Central African Republic": "Central African Rep.",
  "South Sudan": "S. Sudan",
  "North Macedonia": "Macedonia",
  "Solomon Islands": "Solomon Is.",
  "United Republic of Tanzania": "Tanzania"
};

const mapRef = ref(null);
const backendBaseUrl = import.meta.env.VITE_BACKEND_BASE_URL || "http://127.0.0.1:8000";
const activeModelId = ref(MODEL_OPTIONS[0].id);
const lastSeedValue = ref("");

const speedMs = ref(240);
const spreadSpeedKmPerDay = ref(800);
const waveSigmaDays = ref(10);

const loading = ref(false);
const errorMessage = ref("");
const isPlaying = ref(false);
const metadataReady = ref(false);

const timelineFrames = ref([]);
const currentIndex = ref(0);
const metric = ref("predicted_new_cases");
const maxNewCases = ref(0);
const seedCountryCode = ref("");
const seedCountryName = ref("");

const countryCentroids = ref(new Map());
const nameToIso3 = ref(new Map());
const iso3ToName = ref(new Map());

const numberFormatter = new Intl.NumberFormat("en-US", {
  maximumFractionDigits: 0
});

let playTimer = null;
let plotlyClickHandler = null;

const activeModel = computed(
  () => MODEL_OPTIONS.find((option) => option.id === activeModelId.value) || MODEL_OPTIONS[0]
);
const activeModelLabel = computed(() => activeModel.value.label);

const currentFrame = computed(() => timelineFrames.value[currentIndex.value] || null);
const progressText = computed(() => {
  if (!timelineFrames.value.length) {
    return "0 / 0";
  }

  return `${currentIndex.value + 1} / ${timelineFrames.value.length}`;
});
const sliderMax = computed(() => Math.max(0, timelineFrames.value.length - 1));

const clipMaxCases = computed(() => {
  if (!(CLIP_QUANTILE > 0 && CLIP_QUANTILE < 1)) {
    return null;
  }

  const values = [];
  for (const frame of timelineFrames.value) {
    const sourceValues = frame?.new_cases_by_country || {};
    for (const value of Object.values(sourceValues)) {
      values.push(Math.max(0, Number(value) || 0));
    }
  }

  if (!values.length) {
    return null;
  }

  values.sort((left, right) => left - right);
  const index = Math.max(0, Math.min(values.length - 1, Math.floor(CLIP_QUANTILE * (values.length - 1))));
  return values[index];
});

const spreadFrames = computed(() => {
  if (!timelineFrames.value.length) {
    return [];
  }

  const seedName = seedCountryName.value || seedCountryCode.value;
  const seedCentroid = getCentroid(seedName);
  if (!seedCentroid) {
    return timelineFrames.value.map((frame) => frame?.new_cases_by_country || {});
  }

  return timelineFrames.value.map((frame, index) => {
    const sourceValues = frame?.new_cases_by_country || {};
    return buildSpreadCases(sourceValues, index + 1, seedCentroid);
  });
});

const spreadFrameMap = computed(() => spreadFrames.value[currentIndex.value] || {});

const spreadFrameMaxLog = computed(() => {
  const values = Object.values(spreadFrameMap.value || {}).map((value) => Number(value) || 0);
  const maxCases = values.length ? Math.max(...values) : 0;
});

const rankedCountries = computed(() => {
  return Object.entries(spreadFrameMap.value)
    .map(([country, amount]) => ({
      country,
      amount: Number(amount) || 0
    }))
    .sort((left, right) => right.amount - left.amount)
    .slice(0, 8);
});

function normalizeCountryName(name) {
  return COUNTRY_ALIASES[name] || name;
}

function normalizeNameKey(name) {
  return String(name || "")
    .normalize("NFKD")
    .toLowerCase()
    .replace(/[^a-z0-9]/g, "");
}

function formatCases(value) {
  return numberFormatter.format(Math.max(0, Number(value) || 0));
}

function buildPredictionRequest(seedValue) {
  if (activeModelId.value === "traditional_onnx") {
    return {
      origin_country: seedValue
    };
  }

  return {
    seed_country: seedValue
  };
}

function normalizePredictionResponse(payload, modelId) {
  if (modelId === "traditional_onnx") {
    const frames = Array.isArray(payload.frames)
      ? payload.frames.map((frame, index) => ({
          day: index + 1,
          date: frame?.date,
          new_cases_by_country: frame?.infections_by_country || {}
        }))
      : [];

    return {
      frames,
      metric: payload.metric || "predicted_active_cases",
      maxValue: Math.max(0, Number(payload.max_infections) || 0),
      seedCode: payload.origin_country_code || "",
      seedName: payload.origin_country_name || ""
    };
  }

  return {
    frames: Array.isArray(payload.frames) ? payload.frames : [],
    metric: payload.metric || "predicted_new_cases",
    maxValue: Math.max(0, Number(payload.max_new_cases) || 0),
    seedCode: payload.seed_country_code || "",
    seedName: payload.seed_country_name || ""
  };
}

function sigmoid(x) {
  const clamped = Math.max(-60, Math.min(60, Number(x) || 0));
  return 1 / (1 + Math.exp(-clamped));
}

function haversineDistanceKm(origin, target) {
  const [lat1, lon1] = origin;
  const [lat2, lon2] = target;

  const lat1Rad = (lat1 * Math.PI) / 180;
  const lon1Rad = (lon1 * Math.PI) / 180;
  const lat2Rad = (lat2 * Math.PI) / 180;
  const lon2Rad = (lon2 * Math.PI) / 180;

  const dLat = lat2Rad - lat1Rad;
  const dLon = lon2Rad - lon1Rad;

  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1Rad) * Math.cos(lat2Rad) * Math.sin(dLon / 2) ** 2;

  return 6371 * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function applyClip(value) {
  const numeric = Math.max(0, Number(value) || 0);
  const upper = clipMaxCases.value;
  if (upper == null) {
    return numeric;
  }
  return Math.min(numeric, upper);
}

function getCentroid(countryName) {
  if (!countryName) {
    return null;
  }

  const key = normalizeNameKey(countryName);
  const direct = countryCentroids.value.get(key);
  if (direct) {
    return direct;
  }

  const mapAlias = normalizeCountryName(countryName);
  return countryCentroids.value.get(normalizeNameKey(mapAlias)) || null;
}

function toIso3(countryName) {
  if (!countryName) {
    return null;
  }

  const key = normalizeNameKey(countryName);
  const direct = nameToIso3.value.get(key);
  if (direct) {
    return direct;
  }

  const alias = normalizeCountryName(countryName);
  return nameToIso3.value.get(normalizeNameKey(alias)) || null;
}

function toCountryName(iso3) {
  return iso3ToName.value.get(String(iso3 || "").toUpperCase()) || String(iso3 || "");
}

function buildSpreadCases(sourceValues, dayValue, seedCentroid) {
  const speed = Math.max(1, Number(spreadSpeedKmPerDay.value) || 1);
  const sigma = Number(waveSigmaDays.value) || 0;
  const spreadValues = {};

  for (const [country, rawCases] of Object.entries(sourceValues || {})) {
    const predictedCases = applyClip(rawCases);
    const centroid = getCentroid(country);
    if (!centroid) {
      spreadValues[country] = 0;
      continue;
    }

    const distance = haversineDistanceKm(seedCentroid, centroid);
    const delay = distance / speed;
    const activation = sigmoid(dayValue - delay);
    let spreadCases = predictedCases * activation;

    if (sigma > 0) {
      const wave = Math.exp(-((dayValue - delay) ** 2) / (2 * sigma * sigma));
      spreadCases *= wave;
    }

    spreadValues[country] = Math.max(0, spreadCases);
  }

  return spreadValues;
}

function getPlotRows() {
  const rows = [];
  for (const [countryName, spreadCases] of Object.entries(spreadFrameMap.value || {})) {
    const iso3 = toIso3(countryName);
    if (!iso3) {
      continue;
    }

    const raw = Math.max(0, Number(spreadCases) || 0);
    const logValue = Math.log10(raw + 1);
    rows.push({
      iso3,
      countryName,
      raw,
      logValue
    });
  }

  return rows;
}

function getFallbackRows() {
  const rows = [];
  for (const [iso3, countryName] of iso3ToName.value.entries()) {
    rows.push({
      iso3,
      countryName,
      raw: 0,
      logValue: 0
    });
  }
  return rows;
}

function buildPlotlyData() {
  const rows = getPlotRows();
  const finalRows = rows.length ? rows : getFallbackRows();
  return [
    {
      type: "choropleth",
      locationmode: "ISO-3",
      locations: finalRows.map((item) => item.iso3),
      z: finalRows.map((item) => item.logValue),
      text: finalRows.map((item) => item.countryName),
      customdata: finalRows.map((item) => [item.raw]),
      colorscale: "Reds",
      zmin: 0,
      zmax: spreadFrameMaxLog.value,
      marker: {
        line: {
          color: "#555",
          width: 0.4
        }
      },
      hovertemplate:
        "<b>%{text}</b><br>" +
        "Date: " + (currentFrame.value?.date || "--") + "<br>" +
        "Spread Cases: %{customdata[0]:,.2f}<br>" +
        "log10(spread+1): %{z:.3f}<extra></extra>",
      colorbar: {
        title: "log10(spread_cases + 1)"
      }
    }
  ];
}

function buildPlotlyLayout() {
  return {
    title: {
      text: `Global Spread Simulation (Seed: ${seedCountryCode.value || "--"}) - Day ${currentIndex.value + 1} (${currentFrame.value?.date || "--"})`,
      font: { color: "#111", size: 16 }
    },
    paper_bgcolor: "#F6F0E6",
    plot_bgcolor: "#000",
    margin: { l: 10, r: 10, t: 70, b: 10 },
    geo: {
      projection: { type: "natural earth" },
      showframe: true,
      showcoastlines: true,
      coastlinecolor: "#555",
      showland: true,
      landcolor: "#F6F0E6",
      showocean: true,
      oceancolor: "#F6F0E6",
      showlakes: true,
      lakecolor: "#F6F0E6",
      bgcolor: "#F6F0E6"
    },
    font: { color: "#111" }
  };
}

function ensurePlotlyClickHandler() {
  if (!mapRef.value || plotlyClickHandler) {
    return;
  }

  plotlyClickHandler = (eventData) => {
    const point = eventData?.points?.[0];
    if (!point) {
      return;
    }

    const clickedIso3 = String(point.location || "").toUpperCase().trim();
    const clickedName = String(point.text || toCountryName(clickedIso3) || "").trim();
    const seedValue = clickedIso3 || clickedName;

    if (!seedValue) {
      return;
    }

    loadPrediction(seedValue);
  };

  mapRef.value.on("plotly_click", plotlyClickHandler);
}

async function renderPlot() {
  if (!mapRef.value) {
    return;
  }

  const data = buildPlotlyData();
  const layout = buildPlotlyLayout();
  const config = {
    responsive: true,
    displayModeBar: false
  };

  if (mapRef.value.data) {
    await Plotly.react(mapRef.value, data, layout, config);
  } else {
    await Plotly.newPlot(mapRef.value, data, layout, config);
  }

  ensurePlotlyClickHandler();
}

async function loadCountryMetadata() {
  if (metadataReady.value) {
    return;
  }

  let payload = null;
  let lastError = null;

  for (const url of COUNTRY_METADATA_SOURCES) {
    try {
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`countries metadata request failed: ${url}`);
      }

      payload = await response.json();
      break;
    } catch (error) {
      lastError = error;
    }
  }

  if (!payload) {
    throw lastError || new Error("Failed to load country metadata.");
  }

  const centroids = new Map();
  const namesToCode = new Map();
  const codeToName = new Map();

  for (const item of payload) {
    const common = item?.name?.common;
    const official = item?.name?.official;
    const cca3 = String(item?.cca3 || "").toUpperCase().trim();
    const latlng = item?.latlng;

    if (!cca3) {
      continue;
    }

    const preferredName = common || official || cca3;
    codeToName.set(cca3, preferredName);

    const keys = [common, official, cca3].filter(Boolean).map((value) => normalizeNameKey(value));
    for (const key of keys) {
      namesToCode.set(key, cca3);
    }

    if (Array.isArray(latlng) && latlng.length >= 2) {
      const lat = Number(latlng[0]);
      const lon = Number(latlng[1]);
      if (Number.isFinite(lat) && Number.isFinite(lon)) {
        for (const key of keys) {
          centroids.set(key, [lat, lon]);
        }
      }
    }
  }

  countryCentroids.value = centroids;
  nameToIso3.value = namesToCode;
  iso3ToName.value = codeToName;
  metadataReady.value = true;
}

function stopPlayback() {
  isPlaying.value = false;

  if (playTimer) {
    clearInterval(playTimer);
    playTimer = null;
  }
}

function startPlayback() {
  if (!timelineFrames.value.length) {
    return;
  }

  stopPlayback();
  isPlaying.value = true;

  playTimer = setInterval(() => {
    if (!timelineFrames.value.length) {
      return;
    }

    if (currentIndex.value >= timelineFrames.value.length - 1) {
      currentIndex.value = 0;
      return;
    }

    currentIndex.value += 1;
  }, Math.max(120, Number(speedMs.value) || 240));
}

function togglePlayback() {
  if (isPlaying.value) {
    stopPlayback();
  } else {
    startPlayback();
  }
}

function toggleModel() {
  if (loading.value) {
    return;
  }

  const currentIndexValue = MODEL_OPTIONS.findIndex((option) => option.id === activeModelId.value);
  const nextIndex = currentIndexValue === -1 ? 0 : (currentIndexValue + 1) % MODEL_OPTIONS.length;
  activeModelId.value = MODEL_OPTIONS[nextIndex].id;
  stopPlayback();

  if (lastSeedValue.value) {
    loadPrediction(lastSeedValue.value);
    return;
  }

  errorMessage.value = "";
  timelineFrames.value = [];
  currentIndex.value = 0;
  maxNewCases.value = 0;
  seedCountryCode.value = "";
  seedCountryName.value = "";
}

async function loadPrediction(seedCountry) {
  const normalizedSeed = String(seedCountry || "").trim();
  if (!normalizedSeed) {
    return;
  }

  const modelId = activeModelId.value;
  const modelConfig = activeModel.value;
  lastSeedValue.value = normalizedSeed;

  loading.value = true;
  errorMessage.value = "";
  stopPlayback();

  try {
    const endpoint = `${backendBaseUrl.replace(/\/$/, "")}${modelConfig.endpoint}`;
    const response = await fetch(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(buildPredictionRequest(normalizedSeed))
    });

    const data = await response.json();
    if (!response.ok) {
      const detail = data?.detail;
      throw new Error(detail || `Request failed with status ${response.status}`);
    }

    const normalized = normalizePredictionResponse(data, modelId);
    timelineFrames.value = normalized.frames;
    metric.value = normalized.metric;
    maxNewCases.value = normalized.maxValue;
    seedCountryCode.value = normalized.seedCode;
    seedCountryName.value = normalized.seedName;
    currentIndex.value = 0;

    if (!timelineFrames.value.length) {
      errorMessage.value = "The API returned an empty forecast.";
    }

    await nextTick();
    await renderPlot();
  } catch (error) {
    errorMessage.value = error?.message || "Failed to load forecast.";
    timelineFrames.value = [];
    currentIndex.value = 0;
    maxNewCases.value = 0;
    await nextTick();
    await renderPlot();
  } finally {
    loading.value = false;
  }
}

watch(currentIndex, renderPlot);
watch(timelineFrames, renderPlot);
watch(spreadSpeedKmPerDay, renderPlot);
watch(waveSigmaDays, renderPlot);
watch(clipMaxCases, renderPlot);

watch(speedMs, () => {
  if (isPlaying.value) {
    startPlayback();
  }
});

onMounted(async () => {
  try {
    await loadCountryMetadata();
    await nextTick();
    await renderPlot();
  } catch (error) {
    errorMessage.value = error?.message || "Failed to initialize the map.";
  }
});

onBeforeUnmount(async () => {
  stopPlayback();

  if (mapRef.value && plotlyClickHandler) {
    mapRef.value.removeListener("plotly_click", plotlyClickHandler);
    plotlyClickHandler = null;
  }

  if (mapRef.value && mapRef.value.data) {
    await Plotly.purge(mapRef.value);
  }
});
</script>

<template>
  <section class="prediction-card">
    <header class="header-row">
      <div>
        <p class="eyebrow">{{ activeModelLabel }} Forecast API</p>
        <h3 class="title">Global Outbreak Map by Seed Country (Plotly)</h3>
      </div>
      <p class="hint">Metric: {{ metric }}</p>
    </header>

    <div class="toolbar-row">
      <p class="hint">Click a country on the map to request a forecast for the active model.</p>
      <div class="toolbar-actions">
        <button class="ghost" :disabled="loading" @click="toggleModel">
          Model: {{ activeModelLabel }}
        </button>
        <button class="secondary" :disabled="loading || !timelineFrames.length" @click="togglePlayback">
          {{ isPlaying ? "pause" : "play" }}
        </button>
      </div>
    </div>

    <p v-if="errorMessage" class="error-banner">{{ errorMessage }}</p>

    <div class="timeline-shell">
      <div class="meta-row">
        <span class="chip">Seed {{ seedCountryCode || "--" }}</span>
        <span class="chip">Name {{ seedCountryName || "--" }}</span>
        <span class="chip">Model {{ activeModelLabel }}</span>
        <span class="chip">Date {{ currentFrame?.date || "--" }}</span>
        <span class="chip">Frame {{ progressText }}</span>
        <span class="chip">Pred Max {{ formatCases(maxNewCases) }}</span>
        <span class="chip">Spread {{ spreadSpeedKmPerDay }} km/day</span>
        <span class="chip">Sigma {{ waveSigmaDays }}</span>
        <span v-if="loading" class="chip">Loading prediction...</span>
      </div>

      <div ref="mapRef" class="map-canvas"></div>

      <input
        v-model.number="currentIndex"
        class="timeline-slider"
        type="range"
        :min="0"
        :max="sliderMax"
        :disabled="!timelineFrames.length"
      />

      <div class="timeline-labels">
        <span>{{ timelineFrames[0]?.date || "--" }}</span>
        <span>{{ timelineFrames[timelineFrames.length - 1]?.date || "--" }}</span>
      </div>
    </div>

    <ul v-if="rankedCountries.length" class="rank-list">
      <li v-for="(item, index) in rankedCountries" :key="item.country">
        <span class="rank-index">{{ index + 1 }}</span>
        <span class="rank-name">{{ item.country }}</span>
        <span class="rank-value">{{ formatCases(item.amount) }}</span>
      </li>
    </ul>

    <p v-else-if="!loading" class="hint">Click any country to request a forecast and render the spread map.</p>
  </section>
</template>

<style scoped>
.prediction-card {
  display: grid;
  gap: 0.9rem;
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 0.8rem;
}

.eyebrow {
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  font-size: 0.75rem;
  color: #b85c38;
  font-weight: 700;
}

.title {
  margin: 0.28rem 0 0;
  color: #1f2a1f;
}

.hint {
  margin: 0;
  color: #5e6b60;
}

.toolbar-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.8rem;
}

.toolbar-actions {
  display: inline-flex;
  gap: 0.6rem;
  align-items: center;
}

button {
  height: 40px;
  border: 0;
  border-radius: 12px;
  padding: 0 12px;
  font-weight: 700;
  cursor: pointer;
  transition: transform 0.16s ease;
}

button:disabled {
  cursor: not-allowed;
  opacity: 0.72;
}

button:not(:disabled):hover {
  transform: translateY(-1px);
}

.secondary {
  background: linear-gradient(120deg, #1d6b57, #2f8a72);
  color: #f3fff9;
}

.ghost {
  background: #f4efe6;
  color: #27403a;
  border: 1px solid #cfd5c5;
}

.error-banner {
  margin: 0;
  border: 1px solid #efb39a;
  background: #ffe8dd;
  color: #872f17;
  border-radius: 12px;
  padding: 0.55rem 0.7rem;
}

.timeline-shell {
  display: grid;
  gap: 0.75rem;
}

.meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.chip {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  border: 1px solid #c9d5c7;
  background: #edf2e7;
  color: #2e4b44;
  font-size: 0.76rem;
  padding: 0.25rem 0.56rem;
}

.map-canvas {
  width: 100%;
  min-height: 520px;
  border-radius: 16px;
  overflow: hidden;
  background: #000;
  border: 1px solid #262626;
}

.timeline-slider {
  width: 100%;
  accent-color: #b85c38;
}

.timeline-labels {
  display: flex;
  justify-content: space-between;
  font-size: 0.78rem;
  color: #4f6459;
}

.rank-list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 0.45rem;
}

.rank-list li {
  display: grid;
  grid-template-columns: 30px 1fr auto;
  gap: 0.55rem;
  align-items: center;
  border: 1px solid #d2ddca;
  border-radius: 12px;
  background: #f8fbf3;
  padding: 0.42rem 0.58rem;
}

.rank-index {
  width: 22px;
  height: 22px;
  border-radius: 999px;
  background: #ef9a5b;
  color: #fff9f1;
  display: inline-grid;
  place-items: center;
  font-size: 0.72rem;
  font-weight: 700;
}

.rank-name {
  color: #223a34;
}

.rank-value {
  color: #2b564a;
  font-weight: 700;
}

@media (max-width: 1050px) {
  .toolbar-row {
    flex-direction: column;
    align-items: flex-start;
  }
}

@media (max-width: 720px) {
  .map-canvas {
    min-height: 400px;
  }
}
</style>
