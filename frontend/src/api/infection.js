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
