/**
 * App root — sets up routing between Forecast and Accuracy pages.
 */

import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Navbar } from './components';
import ForecastPage from './pages/ForecastPage';
import AccuracyPage from './pages/AccuracyPage';
import './index.css';

export default function App() {
  return (
    <BrowserRouter>
      <Navbar />
      <main className="app-container">
        <Routes>
          <Route path="/" element={<ForecastPage />} />
          <Route path="/accuracy" element={<AccuracyPage />} />
        </Routes>
      </main>
    </BrowserRouter>
  );
}
