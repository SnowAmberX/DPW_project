<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import * as echarts from "echarts";
import { fetchTraditionalOnnxForecast } from "./api/infection";

const WORLD_MAP_SOURCES = [
  "/maps/world.json",
  "https://raw.githubusercontent.com/holtzy/D3-graph-gallery/master/DATA/world.geojson",
];
const COUNTRY_METADATA_SOURCES = [
  "/maps/countries.json",
  "https://raw.githubusercontent.com/mledoze/countries/master/countries.json",
];
const GEO_FETCH_TIMEOUT_MS = 9000;

const COUNTRY_ALIASES = {
  "United States": "United States of America",
  "Democratic Republic of Congo": "Dem. Rep. Congo",
  "North Korea": "Dem. Rep. Korea",
  "South Korea": "Korea",
  "Czechia": "Czech Republic",
  "Bosnia and Herzegovina": "Bosnia and Herz.",
  "Dominican Republic": "Dominican Rep.",
  "Central African Republic": "Central African Rep.",
  "South Sudan": "S. Sudan",
  "North Macedonia": "Macedonia",
  "Solomon Islands": "Solomon Is.",
  "United Republic of Tanzania": "Tanzania",
};
const MAP_TO_TIMELINE_ALIASES = Object.fromEntries(
  Object.entries(COUNTRY_ALIASES).map(([timelineName, mapName]) => [mapName, timelineName]),
);

function toISODateString(value) {
  return value.toISOString().slice(0, 10);
}

const today = new Date();
const defaultForecastEnd = new Date(today);
defaultForecastEnd.setDate(defaultForecastEnd.getDate() + 90);

const chartRef = ref(null);
const mapLoading = ref(false);
const forecastLoading = ref(false);
const errorMessage = ref("");
const backendBaseUrl = ref(import.meta.env.VITE_BACKEND_BASE_URL || "http://127.0.0.1:8000");
const startDate = ref(toISODateString(today));
const endDate = ref(toISODateString(defaultForecastEnd));
const stepDays = ref(29);
const speedMs = ref(220);
const spreadSpeedKmPerDay = ref(680);
const isPlaying = ref(false);
const metric = ref("predicted_active_cases");
const timelineFrames = ref([]);
const maxInfections = ref(1);
const currentIndex = ref(0);
const worldMapReady = ref(false);
const countryCentroids = ref(new Map());
const originCountry = ref("");
const originStartIndex = ref(0);
const originSetByClick = ref(false);

let chartInstance = null;
let playTimer = null;
let chartClickHandler = null;
let timelineAbortController = null;

const numberFormatter = new Intl.NumberFormat("en-US");

const currentFrame = computed(() => timelineFrames.value[currentIndex.value] || null);

const activeOriginCountry = computed(() => {
  if (!originCountry.value || !timelineFrames.value.length) {
    return "";
  }

  return originCountry.value;
});

const elapsedSimulatedDays = computed(() => {
  if (!timelineFrames.value.length) {
    return 0;
  }

  const deltaFrames = Math.max(0, currentIndex.value - originStartIndex.value);
  return deltaFrames * Math.max(1, Number(stepDays.value) || 1);
});

const simulationRadiusKm = computed(() => {
  return elapsedSimulatedDays.value * Math.max(1, Number(spreadSpeedKmPerDay.value) || 1);
});

const renderedFrame = computed(() => {
  return buildSimulatedFrame(currentFrame.value, currentIndex.value);
});

const topCountries = computed(() => {
  if (!renderedFrame.value) {
    return [];
  }

  return Object.entries(renderedFrame.value.infections_by_country || {})
    .map(([name, value]) => ({
      name,
      value: Number(value) || 0,
    }))
    .sort((left, right) => right.value - left.value)
    .slice(0, 8);
});

const progressText = computed(() => {
  if (!timelineFrames.value.length) {
    return "0 / 0";
  }

  return `${currentIndex.value + 1} / ${timelineFrames.value.length}`;
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

function normalizeLookupKey(name) {
  return normalizeNameKey(name).replace(/country$/, "");
}

function toTimelineCountryName(mapCountryName) {
  return MAP_TO_TIMELINE_ALIASES[mapCountryName] || mapCountryName;
}

async function fetchJsonWithTimeout(url, timeoutMs = GEO_FETCH_TIMEOUT_MS) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, { signal: controller.signal });
    if (!response.ok) {
      throw new Error(`request failed: ${url}`);
    }
    return await response.json();
  } finally {
    clearTimeout(timer);
  }
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

async function loadCountryCentroids() {
  if (countryCentroids.value.size) {
    return;
  }

  let payload = null;
  let lastError = null;

  for (const url of COUNTRY_METADATA_SOURCES) {
    try {
      payload = await fetchJsonWithTimeout(url);
      break;
    } catch (error) {
      lastError = error;
    }
  }

  if (!payload) {
    throw lastError || new Error("国家地理中心点数据加载失败。");
  }

  const centroids = new Map();

  for (const item of payload) {
    const common = item?.name?.common;
    const official = item?.name?.official;
    const latlng = item?.latlng;

    if (!Array.isArray(latlng) || latlng.length < 2) {
      continue;
    }

    const lat = Number(latlng[0]);
    const lon = Number(latlng[1]);
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) {
      continue;
    }

    const keys = [common, official].filter(Boolean).map((value) => normalizeNameKey(value));
    for (const key of keys) {
      centroids.set(key, [lat, lon]);
    }
  }

  countryCentroids.value = centroids;
}

function getCentroid(countryName) {
  if (!countryName) {
    return null;
  }

  const direct = countryCentroids.value.get(normalizeNameKey(countryName));
  if (direct) {
    return direct;
  }

  const mapAlias = normalizeCountryName(countryName);
  return countryCentroids.value.get(normalizeNameKey(mapAlias)) || null;
}

function findFirstPositiveDayIndex(countryName) {
  if (!countryName || !timelineFrames.value.length) {
    return 0;
  }

  for (let index = 0; index < timelineFrames.value.length; index += 1) {
    const frame = timelineFrames.value[index];
    const value = Number(frame?.infections_by_country?.[countryName] || 0);
    if (value > 0) {
      return index;
    }
  }

  return 0;
}

function resolveTimelineCountryNameInFrame(mapCountryName, frame) {
  const timelineCountries = Object.keys(frame?.infections_by_country || {});
  if (!timelineCountries.length) {
    return "";
  }

  const timelineName = toTimelineCountryName(mapCountryName);
  if (timelineCountries.includes(timelineName)) {
    return timelineName;
  }

  const normalizedToCountry = new Map(
    timelineCountries.map((name) => [normalizeLookupKey(name), name]),
  );

  const candidates = [
    timelineName,
    mapCountryName,
    COUNTRY_ALIASES[mapCountryName],
    MAP_TO_TIMELINE_ALIASES[mapCountryName],
  ].filter(Boolean);

  for (const candidate of candidates) {
    const resolved = normalizedToCountry.get(normalizeLookupKey(candidate));
    if (resolved) {
      return resolved;
    }
  }

  return "";
}

function calculateForecastDays() {
  const start = new Date(startDate.value);
  const end = new Date(endDate.value);

  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) {
    return 365;
  }

  const diffMs = end.getTime() - start.getTime();
  if (diffMs < 0) {
    return 365;
  }

  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24)) + 1;
  return Math.min(730, Math.max(1, diffDays));
}

function selectOriginCountry(countryName) {
  if (!countryName) {
    return;
  }

  originCountry.value = countryName;
  originSetByClick.value = true;

  loadTimeline(countryName)
    .then(() => {
      startPlayback();
    })
    .catch(() => {
      // loadTimeline already sets user-facing errors.
    });
}

function buildSimulatedFrame(frame, frameIndex) {
  if (!frame) {
    return null;
  }

  const infections = frame.infections_by_country || {};
  const selectedOrigin = activeOriginCountry.value;
  if (!selectedOrigin) {
    return frame;
  }

  const originCentroid = getCentroid(selectedOrigin);
  if (!originCentroid) {
    return frame;
  }

  const frameDelta = Math.max(0, frameIndex - originStartIndex.value);
  const daysSinceOrigin = frameDelta * Math.max(1, Number(stepDays.value) || 1);
  const reachKm = daysSinceOrigin * Math.max(1, Number(spreadSpeedKmPerDay.value) || 1);
  const frontWidthKm = Math.max(Math.max(1, Number(spreadSpeedKmPerDay.value) || 1) * 0.65, 220);

  const simulated = {};

  for (const [country, rawValue] of Object.entries(infections)) {
    const value = Math.max(0, Number(rawValue) || 0);

    if (country === selectedOrigin) {
      simulated[country] = value;
      continue;
    }

    const targetCentroid = getCentroid(country);
    if (!targetCentroid) {
      simulated[country] = 0;
      continue;
    }

    const distanceKm = haversineDistanceKm(originCentroid, targetCentroid);
    if (distanceKm <= reachKm) {
      simulated[country] = value;
      continue;
    }

    if (distanceKm >= reachKm + frontWidthKm) {
      simulated[country] = 0;
      continue;
    }

    const blend = 1 - (distanceKm - reachKm) / frontWidthKm;
    simulated[country] = Math.max(0, value * blend);
  }

  return {
    ...frame,
    infections_by_country: simulated,
  };
}

function toSeriesData(frame) {
  if (!frame) {
    return [];
  }

  return Object.entries(frame.infections_by_country || {}).map(([country, value]) => ({
    name: normalizeCountryName(country),
    value: Number(value) || 0,
  }));
}

function formatInfections(value) {
  return numberFormatter.format(Math.max(0, Math.round(Number(value) || 0)));
}

function toNiceUpperBound(value) {
  const numeric = Math.max(0, Number(value) || 0);
  if (!numeric) {
    return 100000;
  }

  const magnitude = 10 ** Math.floor(Math.log10(numeric));
  const normalized = numeric / magnitude;

  let factor = 10;
  if (normalized <= 1) {
    factor = 1;
  } else if (normalized <= 2) {
    factor = 2;
  } else if (normalized <= 5) {
    factor = 5;
  }

  return factor * magnitude;
}

async function ensureWorldMap() {
  if (worldMapReady.value || echarts.getMap("world")) {
    worldMapReady.value = true;
    return;
  }

  let lastError = null;

  for (const url of WORLD_MAP_SOURCES) {
    try {
      const worldGeoJson = await fetchJsonWithTimeout(url);
      echarts.registerMap("world", worldGeoJson);
      worldMapReady.value = true;
      return;
    } catch (error) {
      lastError = error;
    }
  }

  throw lastError || new Error("Unable to load world map data.");
}

function mapOption() {
  const frame = renderedFrame.value;
  const frameValues = Object.values(frame?.infections_by_country || {}).map((value) =>
    Math.max(0, Number(value) || 0),
  );
  const frameMax = frameValues.length ? Math.max(...frameValues) : 0;
  const backendMax = Math.max(0, Number(maxInfections.value) || 0);
  const visualMax = toNiceUpperBound(Math.max(frameMax, backendMax));

  return {
    animationDurationUpdate: 620,
    animationEasingUpdate: "cubicInOut",
    tooltip: {
      trigger: "item",
      formatter: (params) => {
        const countryName = params.name || "Unknown";
        const infected = params.value == null ? 0 : Number(params.value);
        return `${countryName}<br/>Active cases: ${formatInfections(infected)}`;
      },
    },
    visualMap: {
      min: 0,
      max: visualMax,
      text: ["High", "Low"],
      orient: "horizontal",
      left: "center",
      bottom: 16,
      inRange: {
        color: ["#f3f7ea", "#fff2c6", "#ffcb6f", "#f88445", "#d43a2f"],
      },
      calculable: true,
      textStyle: {
        color: "#314942",
      },
    },
    series: [
      {
        name: metric.value,
        type: "map",
        map: "world",
        roam: true,
        zoom: 1.15,
        emphasis: {
          label: {
            show: false,
          },
          itemStyle: {
            areaColor: "#f0b85f",
          },
        },
        itemStyle: {
          areaColor: "#dde8d8",
          borderColor: "#87a087",
          borderWidth: 0.7,
        },
        data: toSeriesData(frame),
      },
    ],
  };
}

function renderChart() {
  if (!chartRef.value || !worldMapReady.value) {
    return;
  }

  if (!chartInstance) {
    chartInstance = echarts.init(chartRef.value);

    chartClickHandler = (params) => {
      if (!params) {
        return;
      }

      const rawCountry = String(params.name || "").trim();
      if (!rawCountry) {
        return;
      }

      const frame = currentFrame.value;
      const resolvedCountry = resolveTimelineCountryNameInFrame(rawCountry, frame);
      const fallbackCountry = toTimelineCountryName(rawCountry) || rawCountry;

      // Never silently ignore clicks; unresolved names are validated by backend.
      selectOriginCountry(resolvedCountry || fallbackCountry);
    };

    chartInstance.on("click", chartClickHandler);
  }

  chartInstance.setOption(mapOption(), true);
}

function refreshChart() {
  if (!chartInstance) {
    return;
  }

  chartInstance.setOption(mapOption());
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
      currentIndex.value = originStartIndex.value;
      return;
    }

    currentIndex.value += 1;
  }, Math.max(120, Number(speedMs.value) || 420));
}

function togglePlayback() {
  if (isPlaying.value) {
    stopPlayback();
  } else {
    startPlayback();
  }
}

function resizeChart() {
  if (chartInstance) {
    chartInstance.resize();
  }
}

async function requestTraditionalForecast(effectiveOrigin, signal) {
  return fetchTraditionalOnnxForecast({
    baseUrl: backendBaseUrl.value,
    originCountry: effectiveOrigin,
    startDate: startDate.value,
    forecastDays: calculateForecastDays(),
    stepDays: Number(stepDays.value) || 1,
    signal,
  });
}

async function loadTimeline(selectedOrigin = "") {
  const sanitizedOrigin = typeof selectedOrigin === "string" ? selectedOrigin.trim() : "";
  const fallbackOrigin = originCountry.value || "";
  const effectiveOrigin = sanitizedOrigin || fallbackOrigin;

  if (!effectiveOrigin) {
    errorMessage.value = "Please click a country on the map to start forecast.";
    return;
  }

  if (timelineAbortController) {
    timelineAbortController.abort();
  }

  timelineAbortController = new AbortController();
  const currentController = timelineAbortController;

  forecastLoading.value = true;
  errorMessage.value = "";
  stopPlayback();

  try {
    const payload = await requestTraditionalForecast(effectiveOrigin, currentController.signal);

    if (timelineAbortController !== currentController) {
      return;
    }

    timelineFrames.value = Array.isArray(payload.frames) ? payload.frames : [];
    maxInfections.value = Math.max(1, Number(payload.max_infections) || 1);
    metric.value = payload.metric || "predicted_active_cases";

    originCountry.value = payload.origin_country_name || effectiveOrigin;

    if (timelineFrames.value.length && !originCountry.value) {
      const firstFrameCountries = Object.keys(timelineFrames.value[0].infections_by_country || {});
      if (firstFrameCountries.length) {
        originCountry.value = firstFrameCountries.includes("United States")
          ? "United States"
          : firstFrameCountries[0];
      }
    }

    originStartIndex.value = findFirstPositiveDayIndex(originCountry.value);

    currentIndex.value = originStartIndex.value;

    if (!timelineFrames.value.length) {
      errorMessage.value = "Forecast result is empty. Please adjust date range or step size and try again.";
    }

    await nextTick();
    renderChart();
  } catch (error) {
    const isCanceled = error?.name === "CanceledError" || error?.code === "ERR_CANCELED";
    if (isCanceled) {
      return;
    }

    const backendDetail = error?.response?.data?.detail;
    errorMessage.value = backendDetail || error?.message || "Failed to load traditional forecast.";

    timelineFrames.value = [];
    currentIndex.value = 0;
    maxInfections.value = 1;
    await nextTick();
    renderChart();
  } finally {
    if (timelineAbortController === currentController) {
      timelineAbortController = null;
      forecastLoading.value = false;
    }
  }
}

watch(currentIndex, refreshChart);
watch(maxInfections, refreshChart);
watch(originCountry, refreshChart);
watch(originStartIndex, refreshChart);
watch(spreadSpeedKmPerDay, refreshChart);

watch(speedMs, () => {
  if (isPlaying.value) {
    startPlayback();
  }
});

onMounted(async () => {
  mapLoading.value = true;

  try {
    await ensureWorldMap();
    await loadCountryCentroids();
    await nextTick();
    renderChart();
  } catch (error) {
    errorMessage.value = error?.message || "Failed to load world map.";
  } finally {
    mapLoading.value = false;
  }

  window.addEventListener("resize", resizeChart);
});

onBeforeUnmount(() => {
  if (timelineAbortController) {
    timelineAbortController.abort();
    timelineAbortController = null;
  }

  stopPlayback();
  window.removeEventListener("resize", resizeChart);

  if (chartInstance) {
    if (chartClickHandler) {
      chartInstance.off("click", chartClickHandler);
      chartClickHandler = null;
    }

    chartInstance.dispose();
    chartInstance = null;
  }
});
</script>

<template>
  <div class="page-shell">
    <div class="ambient ambient-left"></div>
    <div class="ambient ambient-right"></div>

    <main class="dashboard">
      <header class="hero-card">
        <p class="hero-tag">COVID-19 Geo Timeline</p>
        <h1>Global Infection Prediction</h1>
        <p class="hero-subtitle">
          Use traditional ONNX models to estimate active cases from a selected origin country. Click the map to choose the origin, then compare how spread speed and timeline settings affect the global trajectory.
        </p>
      </header>

      <section class="control-card">
        <div class="field-group url-field">
          <label for="backend-url">Backend URL</label>
          <input id="backend-url" v-model.trim="backendBaseUrl" type="text" placeholder="http://127.0.0.1:8000" />
        </div>

        <div class="field-group">
          <label for="start-date">Start Date</label>
          <input id="start-date" v-model="startDate" type="date" />
        </div>

        <div class="field-group">
          <label for="end-date">End Date</label>
          <input id="end-date" v-model="endDate" type="date" />
        </div>

        <div class="field-group">
          <label for="step-days">Step (days)</label>
          <input id="step-days" v-model.number="stepDays" min="1" max="30" type="number" />
        </div>

        <div class="field-group">
          <label for="speed-ms">Playback (ms)</label>
          <input id="speed-ms" v-model.number="speedMs" min="120" max="2000" step="20" type="number" />
        </div>

        <div class="field-group">
          <label for="spread-speed">Spread (km/day)</label>
          <input
            id="spread-speed"
            v-model.number="spreadSpeedKmPerDay"
            min="80"
            max="2000"
            step="20"
            type="number"
          />
        </div>

        <div class="button-row">
          <button class="primary" :disabled="mapLoading || forecastLoading || !originCountry" @click="loadTimeline(originCountry)">
            {{ forecastLoading ? "loading..." : "reload" }}
          </button>
          <button class="secondary" :disabled="mapLoading || forecastLoading || !timelineFrames.length" @click="togglePlayback">
            {{ isPlaying ? "pause" : "play" }}
          </button>
        </div>
      </section>

      <section class="visual-grid">
        <article class="map-card">
          <div class="map-header">
            <p class="map-title">Active Cases Heatmap</p>
            <div class="map-meta">
              <span v-if="mapLoading" class="chip">Map loading...</span>
              <span v-else-if="forecastLoading" class="chip">Forecast loading...</span>
              <span class="chip">Date {{ currentFrame?.date || "--" }}</span>
              <span class="chip">Frame {{ progressText }}</span>
              <span class="chip">Origin {{ activeOriginCountry || "--" }}</span>
              <span class="chip">Day +{{ elapsedSimulatedDays }}</span>
              <span class="chip">Reach {{ Math.round(simulationRadiusKm) }} km</span>
            </div>
          </div>

          <p v-if="errorMessage" class="error-banner">{{ errorMessage }}</p>

          <div ref="chartRef" class="map-canvas"></div>

          <div class="timeline-panel">
            <input
              v-model.number="currentIndex"
              class="timeline-slider"
              type="range"
              :min="0"
              :max="Math.max(timelineFrames.length - 1, 0)"
              :disabled="!timelineFrames.length"
            />
            <div class="timeline-labels">
              <span>{{ timelineFrames[0]?.date || "--" }}</span>
              <span>{{ timelineFrames[timelineFrames.length - 1]?.date || "--" }}</span>
            </div>
          </div>
        </article>

        <aside class="rank-card">
          <h2>Top 8 Countries</h2>
          <p class="rank-hint">Sorted by estimated active cases</p>

          <ul v-if="topCountries.length" class="rank-list">
            <li v-for="(item, index) in topCountries" :key="item.name">
              <span class="rank-index">{{ index + 1 }}</span>
              <span class="rank-name">{{ item.name }}</span>
              <span class="rank-value">{{ formatInfections(item.value) }}</span>
            </li>
          </ul>
          <p v-else class="empty-text">No data available</p>
        </aside>
      </section>

    </main>
  </div>
</template>

<style scoped>
.page-shell {
  --ink-900: #102521;
  --ink-600: #35534b;
  --mint-100: #eef4e7;
  --mint-200: #dfead7;
  --accent-500: #e8703a;
  --accent-700: #bc4a1e;

  position: relative;
  min-height: 100vh;
  overflow: hidden;
  padding: 28px 20px 32px;
  background:
    radial-gradient(circle at 15% 15%, #f5e5b9 0%, transparent 36%),
    radial-gradient(circle at 84% 80%, #d4ecd8 0%, transparent 44%),
    linear-gradient(138deg, #edf3e7 0%, #e4ece0 42%, #d7e2d5 100%);
}

.ambient {
  position: absolute;
  border-radius: 50%;
  filter: blur(14px);
  opacity: 0.55;
  animation: drift 11s ease-in-out infinite;
  pointer-events: none;
}

.ambient-left {
  width: 360px;
  height: 360px;
  left: -120px;
  top: 48px;
  background: #ffd7a4;
}

.ambient-right {
  width: 300px;
  height: 300px;
  right: -90px;
  bottom: 90px;
  background: #b8dfca;
  animation-delay: 1.3s;
}

.dashboard {
  position: relative;
  z-index: 1;
  max-width: 1320px;
  margin: 0 auto;
  display: grid;
  gap: 16px;
  animation: rise 560ms ease-out;
}

.hero-card,
.control-card,
.map-card,
.rank-card {
  background: rgba(250, 252, 246, 0.88);
  border: 1px solid rgba(66, 98, 88, 0.18);
  border-radius: 20px;
  box-shadow: 0 16px 30px rgba(31, 58, 48, 0.1);
  backdrop-filter: blur(2px);
}

.hero-card {
  padding: 22px 24px;
}

.hero-tag {
  margin: 0;
  color: var(--ink-600);
  font-size: 12px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  font-weight: 700;
}

h1 {
  margin: 8px 0 8px;
  font-family: "Sora", "Segoe UI", sans-serif;
  font-size: clamp(24px, 3vw, 38px);
  line-height: 1.1;
  color: var(--ink-900);
}

.hero-subtitle {
  margin: 0;
  color: var(--ink-600);
  max-width: 760px;
  line-height: 1.55;
}

.control-card {
  padding: 16px;
  display: grid;
  gap: 12px;
  grid-template-columns: 1.3fr repeat(5, minmax(120px, 1fr)) auto;
  align-items: end;
}

.field-group {
  display: grid;
  gap: 8px;
}

.field-group label {
  font-size: 12px;
  letter-spacing: 0.03em;
  color: #35584f;
  font-weight: 700;
}

.field-group input {
  height: 42px;
  border: 1px solid #bfd3be;
  border-radius: 12px;
  padding: 0 12px;
  color: #18322d;
  background: #f4f9f0;
}

.field-group input:focus {
  outline: 2px solid rgba(237, 146, 76, 0.35);
  border-color: #df8a4b;
}

.button-row {
  display: flex;
  gap: 10px;
}

button {
  height: 42px;
  border: 0;
  border-radius: 12px;
  padding: 0 16px;
  font-weight: 700;
  cursor: pointer;
  transition: transform 0.16s ease, filter 0.16s ease;
}

button:disabled {
  cursor: not-allowed;
  filter: grayscale(0.2);
}

button:not(:disabled):hover {
  transform: translateY(-1px);
}

.primary {
  background: linear-gradient(120deg, var(--accent-500), #f09052);
  color: #fff9f2;
}

.secondary {
  background: linear-gradient(120deg, #204f43, #2e6f5e);
  color: #eefcf7;
}

.visual-grid {
  display: grid;
  gap: 14px;
  grid-template-columns: minmax(0, 3fr) minmax(280px, 1fr);
}

.map-card {
  padding: 12px;
  min-height: 600px;
  display: grid;
  grid-template-rows: auto 1fr auto;
  gap: 10px;
}

.map-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 4px 6px;
}

.map-title {
  margin: 0;
  font-family: "Sora", "Segoe UI", sans-serif;
  font-size: 18px;
  color: #17332d;
}

.map-meta {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.chip {
  background: #e3ece0;
  border: 1px solid #b3c7b1;
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 12px;
  color: #26453e;
}

.map-canvas {
  width: 100%;
  min-height: 500px;
}

.timeline-panel {
  padding: 2px 10px 10px;
}

.timeline-slider {
  width: 100%;
  accent-color: #d56938;
}

.timeline-labels {
  display: flex;
  justify-content: space-between;
  color: #3b554f;
  font-size: 12px;
}

.rank-card {
  padding: 16px;
  min-height: 600px;
  display: grid;
  align-content: start;
  gap: 10px;
}

.rank-card h2 {
  margin: 0;
  font-family: "Sora", "Segoe UI", sans-serif;
  color: #17332d;
}

.rank-hint {
  margin: 0;
  color: #4a6861;
  font-size: 13px;
}

.rank-list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 8px;
}

.rank-list li {
  display: grid;
  grid-template-columns: 34px 1fr auto;
  align-items: center;
  gap: 10px;
  background: #edf4ea;
  border: 1px solid #c9d9c6;
  border-radius: 12px;
  padding: 8px 10px;
}

.rank-index {
  display: inline-grid;
  place-items: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #f2a262;
  color: #fffaf3;
  font-size: 12px;
  font-weight: 700;
}

.rank-name {
  color: #1f3d36;
}

.rank-value {
  color: #2e584f;
  font-weight: 700;
}

.empty-text {
  margin: 0;
  color: #617a72;
}

.error-banner {
  margin: 0 0 8px;
  background: #ffe7dc;
  border: 1px solid #f3b097;
  color: #8a2f16;
  border-radius: 12px;
  padding: 10px 12px;
  font-size: 14px;
  font-weight: 600;
}

@media (max-width: 1150px) {
  .control-card {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .url-field {
    grid-column: 1 / -1;
  }

  .button-row {
    grid-column: 1 / -1;
  }

  .visual-grid {
    grid-template-columns: 1fr;
  }

  .rank-card {
    min-height: initial;
  }
}

@media (max-width: 760px) {
  .page-shell {
    padding: 16px 12px 22px;
  }

  .hero-card,
  .control-card,
  .map-card,
  .rank-card {
    border-radius: 16px;
  }

  .control-card {
    grid-template-columns: 1fr;
  }

  .button-row {
    width: 100%;
  }

  .button-row button {
    flex: 1;
  }

  .map-canvas {
    min-height: 380px;
  }
}

@keyframes rise {
  from {
    opacity: 0;
    transform: translateY(16px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes drift {
  0%,
  100% {
    transform: translateY(0) scale(1);
  }
  50% {
    transform: translateY(-16px) scale(1.04);
  }
}
</style>
