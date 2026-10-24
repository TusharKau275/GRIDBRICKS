/**
 * Shared UI components: Navbar, KPI cards, Loading, Error states.
 */

import { NavLink } from 'react-router-dom';

/* ---- Wind icon (SVG) ---- */
export function WindIcon({ size = 24 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
         strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17.7 7.7a2.5 2.5 0 1 1 1.8 4.3H2" />
      <path d="M9.6 4.6A2 2 0 1 1 11 8H2" />
      <path d="M12.6 19.4A2 2 0 1 0 14 16H2" />
    </svg>
  );
}

/* ---- Info icon ---- */
export function InfoIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
         strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="16" x2="12" y2="12" />
      <line x1="12" y1="8" x2="12.01" y2="8" />
    </svg>
  );
}

/* ---- Navbar ---- */
export function Navbar() {
  return (
    <nav className="navbar">
      <div className="navbar-inner">
        <NavLink to="/" className="navbar-brand">
          <WindIcon />
          <span>Wind Forecast Monitor</span>
        </NavLink>
        <div className="navbar-links">
          <NavLink to="/" end className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
            Forecast
          </NavLink>
          <NavLink to="/accuracy" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
            Accuracy
          </NavLink>
        </div>
      </div>
    </nav>
  );
}

/* ---- KPI Card ---- */
export function KpiCard({ label, value, unit, detail, color = 'cyan' }) {
  return (
    <div className={`kpi-card ${color} animate-in`}>
      <div className="kpi-label">{label}</div>
      <div className="kpi-value">
        {value != null ? value.toLocaleString() : '—'}
        {unit && <span className="kpi-unit">{unit}</span>}
      </div>
      {detail && <div className="kpi-detail">{detail}</div>}
    </div>
  );
}

/* ---- Loading ---- */
export function Loading({ message = 'Loading data…' }) {
  return (
    <div className="loading-container">
      <div className="spinner" />
      <div className="loading-text">{message}</div>
    </div>
  );
}

/* ---- Error ---- */
export function ErrorMessage({ message }) {
  return (
    <div className="error-container">
      <h3>⚠ Something went wrong</h3>
      <p>{message}</p>
      <p style={{ marginTop: '0.5rem', fontSize: '0.8rem' }}>
        Make sure the backend is running on port 8000.
      </p>
    </div>
  );
}

/* ---- Info Note ---- */
export function InfoNote({ children }) {
  return (
    <div className="info-note">
      <InfoIcon />
      <div>{children}</div>
    </div>
  );
}
