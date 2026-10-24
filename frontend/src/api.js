/**
 * API client for the Wind Forecast Monitor backend.
 * Uses VITE_API_URL env var for deployment, falls back to localhost:8000.
 */

const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function fetchJSON(path) {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`API error ${res.status}: ${res.statusText}`);
  return res.json();
}

export function fetchHealth() {
  return fetchJSON('/api/health');
}

export function fetchDates() {
  return fetchJSON('/api/dates');
}

export function fetchForecast(date, cutoffHour = 9) {
  return fetchJSON(`/api/forecast?date=${date}&cutoff_hour=${cutoffHour}`);
}

export function fetchMetrics(cutoffHour = 9) {
  return fetchJSON(`/api/metrics?cutoff_hour=${cutoffHour}`);
}

export function fetchHorizonError() {
  return fetchJSON('/api/horizon-error');
}
