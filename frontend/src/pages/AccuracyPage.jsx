/**
 * Page 2 — Forecast Accuracy.
 *
 * Shows monthly KPIs, error-by-hour bar chart, error-vs-horizon chart,
 * and error-by-wind-level chart.
 */

import { useState, useEffect, useMemo } from 'react';
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, Cell,
} from 'recharts';
import { fetchMetrics, fetchHorizonError } from '../api';
import { KpiCard, Loading, ErrorMessage, InfoNote } from '../components';

/* Colour palette for charts */
const COLORS = {
  cyan: '#06b6d4',
  violet: '#8b5cf6',
  emerald: '#10b981',
  amber: '#f59e0b',
  rose: '#f43f5e',
  slate: '#64748b',
};

const WIND_COLORS = {
  Low: COLORS.cyan,
  Medium: COLORS.amber,
  High: COLORS.rose,
};

export default function AccuracyPage() {
  const [cutoffHour, setCutoffHour] = useState(9);
  const [metrics, setMetrics] = useState(null);
  const [horizon, setHorizon] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    Promise.all([
      fetchMetrics(cutoffHour),
      fetchHorizonError(),
    ])
      .then(([m, h]) => {
        setMetrics(m);
        setHorizon(h);
        setLoading(false);
      })
      .catch(e => { setError(e.message); setLoading(false); });
  }, [cutoffHour]);

  // Error by hour chart data
  const hourData = useMemo(() => {
    if (!metrics?.by_hour) return [];
    return metrics.by_hour.map(h => ({
      hour: `${String(h.hour).padStart(2, '0')}:00`,
      MAE: h.mae,
      Bias: h.bias,
    }));
  }, [metrics]);

  // Horizon chart data
  const horizonData = useMemo(() => {
    if (!horizon?.buckets) return [];
    return horizon.buckets.map(b => ({
      bucket: b.bucket,
      MAE: b.mae,
      RMSE: b.rmse,
      n: b.n,
    }));
  }, [horizon]);

  // Wind level data
  const windData = useMemo(() => {
    if (!metrics?.by_wind_level) return [];
    return metrics.by_wind_level.map(w => ({
      level: w.wind_level,
      MAE: w.mae,
      Bias: w.bias,
      range: w.range,
      RMSE: w.rmse,
    }));
  }, [metrics]);

  if (loading) return <Loading message="Computing accuracy metrics…" />;
  if (error) return <ErrorMessage message={error} />;

  const o = metrics?.overall;

  return (
    <div className="animate-in">
      <div className="page-header">
        <h1>Forecast Accuracy</h1>
        <p>
          How accurate have the wind forecasts been across January 2026?
          These metrics help you decide how much safety margin to add when
          buying power on the day-ahead market.
        </p>
      </div>

      {/* Cutoff selector */}
      <div className="controls-bar">
        <div className="control-group">
          <label htmlFor="cutoff-accuracy">Decision Cutoff (D-1)</label>
          <select
            id="cutoff-accuracy"
            value={cutoffHour}
            onChange={e => setCutoffHour(Number(e.target.value))}
          >
            {Array.from({ length: 24 }, (_, i) => (
              <option key={i} value={i}>{String(i).padStart(2, '0')}:00 UK</option>
            ))}
          </select>
        </div>
      </div>

      {/* KPI Cards */}
      {o && (
        <div className="kpi-grid">
          <KpiCard label="MAE" value={o.mae} unit="MW" color="cyan"
                   detail="Average absolute error" />
          <KpiCard label="RMSE" value={o.rmse} unit="MW" color="violet"
                   detail="Penalises large errors more" />
          <KpiCard label="Bias" value={o.bias} unit="MW"
                   color={o.bias >= 0 ? 'amber' : 'green'}
                   detail={o.bias >= 0 ? 'Tends to over-forecast' : 'Tends to under-forecast'} />
          <KpiCard label="P50 Error" value={o.p50} unit="MW" color="cyan"
                   detail="Median absolute error" />
          <KpiCard label="P90 Error" value={o.p90} unit="MW" color="red"
                   detail="90th percentile abs error" />
          <KpiCard label="P95 Error" value={o.p95} unit="MW" color="red"
                   detail="95th percentile abs error" />
        </div>
      )}

      <InfoNote>
        <strong>What these numbers mean:</strong> MAE is the average mistake size.
        Bias shows whether forecasts systematically over- or under-predict.
        P90 means 90% of the time the error was smaller than this — use it as a
        rule-of-thumb safety margin.
        {o?.n && ` Based on ${o.n.toLocaleString()} half-hour observations.`}
      </InfoNote>

      {/* Charts grid */}
      <div className="chart-grid two-col">
        {/* Error by hour */}
        <div className="chart-container animate-in">
          <h3>Error by Hour of Day</h3>
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={hourData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.08)" />
              <XAxis dataKey="hour" tick={{ fontSize: 10 }} interval={1} />
              <YAxis tick={{ fontSize: 11 }} label={{ value: 'MW', angle: -90, position: 'insideLeft', style: { fill: '#64748b', fontSize: 12 } }} />
              <Tooltip
                contentStyle={{ background: '#1a2235', border: '1px solid rgba(6,182,212,0.3)', borderRadius: 8, fontSize: 13 }}
                labelStyle={{ color: '#f1f5f9', fontWeight: 600 }}
              />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Bar dataKey="MAE" fill={COLORS.cyan} radius={[4, 4, 0, 0]} name="MAE (MW)" />
              <Bar dataKey="Bias" fill={COLORS.violet} radius={[4, 4, 0, 0]} name="Bias (MW)" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Error by wind level */}
        <div className="chart-container animate-in">
          <h3>Error by Wind Level</h3>
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={windData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.08)" />
              <XAxis dataKey="level" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 11 }} label={{ value: 'MW', angle: -90, position: 'insideLeft', style: { fill: '#64748b', fontSize: 12 } }} />
              <Tooltip
                contentStyle={{ background: '#1a2235', border: '1px solid rgba(6,182,212,0.3)', borderRadius: 8, fontSize: 13 }}
                labelStyle={{ color: '#f1f5f9', fontWeight: 600 }}
                formatter={(value, name, props) => {
                  const range = props.payload.range;
                  return [`${value} MW${range ? ` (${range})` : ''}`, name];
                }}
              />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Bar dataKey="MAE" name="MAE (MW)" radius={[4, 4, 0, 0]}>
                {windData.map((entry, i) => (
                  <Cell key={i} fill={WIND_COLORS[entry.level] || COLORS.slate} />
                ))}
              </Bar>
              <Bar dataKey="RMSE" fill={COLORS.violet} radius={[4, 4, 0, 0]} name="RMSE (MW)" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Error vs horizon (full width) */}
      <div className="chart-container animate-in" style={{ marginBottom: '1.5rem' }}>
        <h3>Error vs Forecast Horizon</h3>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '1rem' }}>
          How does accuracy degrade as the forecast looks further ahead?
          Shorter horizons are generally more accurate.
        </p>
        <ResponsiveContainer width="100%" height={340}>
          <BarChart data={horizonData} margin={{ top: 10, right: 20, left: 10, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.08)" />
            <XAxis dataKey="bucket" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} label={{ value: 'MW', angle: -90, position: 'insideLeft', style: { fill: '#64748b', fontSize: 12 } }} />
            <Tooltip
              contentStyle={{ background: '#1a2235', border: '1px solid rgba(6,182,212,0.3)', borderRadius: 8, fontSize: 13 }}
              labelStyle={{ color: '#f1f5f9', fontWeight: 600 }}
              formatter={(value, name, props) => [`${value} MW (n=${props.payload.n})`, name]}
            />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Bar dataKey="MAE" fill={COLORS.cyan} radius={[4, 4, 0, 0]} name="MAE (MW)" />
            <Bar dataKey="RMSE" fill={COLORS.violet} radius={[4, 4, 0, 0]} name="RMSE (MW)" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <InfoNote>
        <strong>Reading the horizon chart:</strong> Each bar shows accuracy for forecasts
        made a certain number of hours before the target period. Shorter lead times
        (0-6h) tend to be more accurate. If your cutoff allows it, waiting for a later
        forecast can reduce your exposure.
      </InfoNote>
    </div>
  );
}
