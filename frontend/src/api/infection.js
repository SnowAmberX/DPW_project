import axios from "axios";

const DEFAULT_BASE_URL = import.meta.env.VITE_BACKEND_BASE_URL || "http://127.0.0.1:8000";

export async function fetchInfectionTimeline({
  baseUrl = DEFAULT_BASE_URL,
  startDate = "",
  endDate = "",
  stepDays = 14,
} = {}) {
  const target = `${baseUrl.replace(/\/$/, "")}/api/v1/infections/timeline`;
  const params = { step_days: stepDays };

  if (startDate) {
    params.start_date = startDate;
  }

  if (endDate) {
    params.end_date = endDate;
  }

  const response = await axios.get(target, {
    params,
    timeout: 20000,
  });

  return response.data;
}

export async function fetchTraditionalOnnxForecast({
  baseUrl = DEFAULT_BASE_URL,
  originCountry,
  forecastDays = 365,
  startDate = "",
  stepDays = 1,
  signal,
} = {}) {
  const target = `${baseUrl.replace(/\/$/, "")}/api/v1/infections/traditional-onnx/forecast`;

  const payload = {
    origin_country: originCountry,
    forecast_days: forecastDays,
    step_days: stepDays,
  };

  if (startDate) {
    payload.start_date = startDate;
  }

  const response = await axios.post(target, payload, {
    timeout: 180000,
    signal,
  });

  return response.data;
}
