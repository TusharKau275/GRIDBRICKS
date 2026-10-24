/**
 * Page 1 — Forecast for a delivery day.
 *
 * Shows a line chart of forecast vs actual with uncertainty band,
 * day-level KPIs, and the publish times used.
 */

import { useState, useEffect, useMemo } from 'react';
import {
  ComposedChart, Line, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, ReferenceLine,
} from 'recharts';
import { fetchDates, fetchForecast } from '../api';
import { KpiCard, Loading, ErrorMessage, InfoNote } from '../components';

/** Format ISO timestamp to UK time string (HH:mm) */
function toUKTime(iso) {
  return new Date(iso).toLocaleTimeString('en-GB', {
    timeZone: 'Europe/London',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/** Format ISO to UK date+time */
function toUKDateTime(iso) {
  return new Date(iso).toLocaleString('en-GB', {
    timeZone: 'Europe/London',
    day: 'numeric', month: 'short',
    hour: '2-digit', minute: '2-digit',
  });
}

export default function ForecastPage() {
  const [dates, setDates] = useState([]);
  const [selectedDate, setSelectedDate] = useState('');
  const [cutoffHour, setCutoffHour] = useState(9);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Load available dates on mount
  useEffect(() => {
    fetchDates()
      .then(d => {
        setDates(d.dates);
        // default to first date with a nice offset (3rd date to show more data)
        if (d.dates.length > 2) setSelectedDate(d.dates[2]);
        else if (d.dates.length > 0) setSelectedDate(d.dates[0]);
        setLoading(false);
      })
      .catch(e => { setError(e.message); setLoading(false); });
  }, []);

  // Fetch forecast data when date or cutoff changes
  useEffect(() => {
    if (!selectedDate) return;
    setLoading(true);
    setError(null);
    fetchForecast(selectedDate, cutoffHour)
      .then(d => { setData(d); setLoading(false); })
      .catch(e => { setError(e.message); setLoading(false); });
  }, [selectedDate, cutoffHour]);

  // Prepare chart data
  const chartData = useMemo(() => {
    if (!data?.points) return [];
    return data.points.map(p => ({
      time: toUKTime(p.startTime),
      forecast: p.forecast,
      actual: p.actual,
      bandUpper: p.band_upper,
      bandLower: p.band_lower,
      // For area fill between upper and lower
      band: p.band_upper != null ? [p.band_lower, p.band_upper] : null,
    }));
  }, [data]);

  // Unique publish times used
  const publishTimes = useMemo(() => {
    if (!data?.points) return [];
    const unique = [...new Set(data.points.map(p => p.publishTime))];
    return unique.sort();
  }, [data]);

  if (loading && !data) return <Loading message="Loading forecast data…" />;
  if (error) return <ErrorMessage message={error} />;

  return (
    <div className="animate-in">
      <div className="page-header">
        <h1>Forecast for Delivery Day</h1>
        <p>
          View the latest wind generation forecast available at decision time vs actual output.
          The shaded band shows the ±P90 error from the whole month — this is where 90% of
          forecast errors fall, helping you judge what safety margin to apply.
        </p>
      </div>

      {/* Controls */}
      <div className="controls-bar">
        <div className="control-group">
          <label htmlFor="date-picker">Delivery Date</label>
          <input
            id="date-picker"
            type="date"
            value={selectedDate}
            min={dates[0]}
            max={dates[dates.length - 1]}
            onChange={e => setSelectedDate(e.target.value)}
          />
        </div>
        <div className="control-group">
          <label htmlFor="cutoff-select">Decision Cutoff (D-1)</label>
          <select
            id="cutoff-select"
            value={cutoffHour}
            onChange={e => setCutoffHour(Number(e.target.value))}
          >
            {Array.from({ length: 24 }, (_, i) => (
              <option key={i} value={i}>{String(i).padStart(2, '0')}:00 UK</option>
            ))}
          </select>
        </div>
      </div>

      {/* Day KPIs */}
      {data?.kpi && (
        <div className="kpi-grid">
          <KpiCard label="MAE" value={data.kpi.mae} unit="MW" color="cyan"
                   detail="Mean absolute error" />
          <KpiCard label="RMSE" value={data.kpi.rmse} unit="MW" color="violet"
                   detail="Root mean square error" />
          <KpiCard label="Bias" value={data.kpi.bias} unit="MW" color={data.kpi.bias >= 0 ? 'amber' : 'green'}
                   detail={data.kpi.bias >= 0 ? 'Over-forecasting on avg' : 'Under-forecasting on avg'} />
          <KpiCard label="Uncertainty (P90)" value={data.uncertainty_mw} unit="MW" color="red"
                   detail="Monthly P90 abs error" />
        </div>
      )}

      {/* Main chart */}
      <div className="chart-container animate-in">
        <h3>Wind Generation — {selectedDate}</h3>
        <ResponsiveContainer width="100%" height={420}>
          <ComposedChart data={chartData} margin={{ top: 10, right: 20, left: 10, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.08)" />
            <XAxis dataKey="time" tick={{ fontSize: 11 }} interval="preserveStartEnd" />
            <YAxis
              tick={{ fontSize: 11 }}
              label={{ value: 'MW', angle: -90, position: 'insideLeft', style: { fill: '#64748b', fontSize: 12 } }}
            />
            <Tooltip
              contentStyle={{
                background: '#1a2235', border: '1px solid rgba(6,182,212,0.3)',
                borderRadius: 8, fontSize: 13
              }}
              labelStyle={{ color: '#f1f5f9', fontWeight: 600 }}
            />
            <Legend wrapperStyle={{ fontSize: 13, paddingTop: 8 }} />

            {/* Uncertainty band */}
            <Area
              dataKey="bandUpper"
              stroke="none"
              fill="rgba(139,92,246,0.12)"
              name="P90 band (upper)"
              type="monotone"
              dot={false}
              legendType="none"
            />
            <Area
              dataKey="bandLower"
              stroke="none"
              fill="var(--bg-card)"
              name="P90 band (lower)"
              type="monotone"
              dot={false}
              legendType="none"
            />

            {/* Forecast line */}
            <Line
              dataKey="forecast"
              stroke="#06b6d4"
              strokeWidth={2.5}
              dot={false}
              name="Forecast"
              type="monotone"
            />
            {/* Actual line */}
            <Line
              dataKey="actual"
              stroke="#10b981"
              strokeWidth={2}
              dot={false}
              name="Actual"
              type="monotone"
              strokeDasharray="4 2"
            />
          </ComposedChart>
        </ResponsiveContainer>

        {/* Publish times used */}
        {publishTimes.length > 0 && (
          <div className="publish-times">
            <span>Forecasts published:</span>
            {publishTimes.slice(0, 6).map(pt => (
              <span key={pt} className="tag">{toUKDateTime(pt)}</span>
            ))}
            {publishTimes.length > 6 && (
              <span className="tag">+{publishTimes.length - 6} more</span>
            )}
          </div>
        )}
      </div>

      <InfoNote>
        <strong>How to read this chart:</strong> The cyan line shows the forecast
        that was available by {String(cutoffHour).padStart(2, '0')}:00 UK time on the
        day before delivery. The green dashed line is what actually happened. If
        the actual falls within the shaded band most of the time, the P90 margin
        is a reasonable safety buffer for trading decisions.
      </InfoNote>
    </div>
  );
}
