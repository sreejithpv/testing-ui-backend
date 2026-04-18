import { useState } from "react";
import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import Dashboard from "./components/Dashboard";
import ConfigPanel from "./components/ConfigPanel";
import TreePage from "./components/TreePage";

// Default configuration — these match the backend defaults
const DEFAULT_CONFIG = {
  timeframe: "5m",
  sort_by: "pct_change",
  sort_order: "desc",
  max_results: 20,
  refreshInterval: 5000, // milliseconds (5 seconds)
};

export default function App() {
  const [config, setConfig] = useState(DEFAULT_CONFIG);
  const [configOpen, setConfigOpen] = useState(false);

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-[var(--color-surface)] text-gray-100">
        {/* ── Header ── */}
        <header className="sticky top-0 z-20 border-b border-[var(--color-border)] bg-[var(--color-surface)]/95 backdrop-blur-sm">
          <div className="mx-auto flex max-w-screen-2xl flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6">
            <div className="flex items-center gap-3">
              <span className="text-2xl">📈</span>
              <div>
                <h1 className="text-lg font-bold tracking-tight text-white">
                  My Trading Helper
                </h1>
                <p className="text-xs text-gray-500">
                  Intraday Breakout & Reversal Scanner
                </p>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <Link
                to="/"
                className="rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] px-3 py-1.5 text-xs text-gray-300 transition hover:border-gray-600 hover:text-white"
              >
                Dashboard
              </Link>
              <Link
                to="/test/tree"
                className="rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] px-3 py-1.5 text-xs text-gray-300 transition hover:border-gray-600 hover:text-white"
              >
                Test Tree
              </Link>

              <div className="flex rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] p-0.5">
                {["1m", "5m", "10m"].map((tf) => (
                  <button
                    key={tf}
                    onClick={() => setConfig((c) => ({ ...c, timeframe: tf }))}
                    className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
                      config.timeframe === tf
                        ? "bg-blue-600 text-white"
                        : "text-gray-400 hover:text-white"
                    }`}
                  >
                    {tf}
                  </button>
                ))}
              </div>

              {/* Config Button */}
              <button
                onClick={() => setConfigOpen(!configOpen)}
                className="rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] px-3 py-1.5 text-xs text-gray-400 transition-colors hover:border-gray-600 hover:text-white"
              >
                ⚙️ Settings
              </button>
            </div>
          </div>
        </header>

        {/* ── Config Panel (collapsible) ── */}
        {configOpen && (
          <ConfigPanel
            config={config}
            setConfig={setConfig}
            onClose={() => setConfigOpen(false)}
          />
        )}

        {/* ── Main Content ── */}
        <main className="mx-auto max-w-screen-2xl px-4 py-6 sm:px-6">
          <Routes>
            <Route path="/" element={<Dashboard config={config} />} />
            <Route path="/test/tree" element={<TreePage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
