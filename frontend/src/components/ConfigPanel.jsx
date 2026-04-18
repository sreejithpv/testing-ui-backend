/**
 * ConfigPanel — A collapsible settings panel for adjusting scanner parameters.
 *
 * Users can change:
 *  - Max results (how many stocks to show per column)
 *  - Sort by (% change, score, or volume)
 *  - Sort order (ascending / descending)
 *  - Auto-refresh interval (3s, 5s, 10s, 30s)
 */

export default function ConfigPanel({ config, setConfig, onClose }) {
  // Helper: update a single config field
  const update = (key, value) => {
    setConfig((prev) => ({ ...prev, [key]: value }));
  };

  return (
    <div className="border-b border-[var(--color-border)] bg-[var(--color-card)]">
      <div className="mx-auto max-w-screen-2xl px-4 py-5 sm:px-6">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="font-semibold text-white">Scanner Settings</h3>
          <button
            onClick={onClose}
            className="text-gray-500 transition-colors hover:text-white"
          >
            ✕
          </button>
        </div>

        <div className="grid grid-cols-2 gap-6 sm:grid-cols-4">
          {/* Max Results */}
          <div>
            <label className="mb-1.5 block text-xs font-medium text-gray-400">
              Max Results
            </label>
            <select
              value={config.max_results}
              onChange={(e) => update("max_results", Number(e.target.value))}
              className="w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm text-white focus:border-blue-500 focus:outline-none"
            >
              {[5, 10, 15, 20, 30, 50].map((n) => (
                <option key={n} value={n}>
                  {n} stocks
                </option>
              ))}
            </select>
          </div>

          {/* Sort By */}
          <div>
            <label className="mb-1.5 block text-xs font-medium text-gray-400">
              Sort By
            </label>
            <select
              value={config.sort_by}
              onChange={(e) => update("sort_by", e.target.value)}
              className="w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm text-white focus:border-blue-500 focus:outline-none"
            >
              <option value="pct_change">% Change</option>
              <option value="score">Score</option>
              <option value="volume">Volume</option>
            </select>
          </div>

          {/* Sort Order */}
          <div>
            <label className="mb-1.5 block text-xs font-medium text-gray-400">
              Sort Order
            </label>
            <select
              value={config.sort_order}
              onChange={(e) => update("sort_order", e.target.value)}
              className="w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm text-white focus:border-blue-500 focus:outline-none"
            >
              <option value="desc">Descending (highest first)</option>
              <option value="asc">Ascending (lowest first)</option>
            </select>
          </div>

          {/* Auto-Refresh Interval */}
          <div>
            <label className="mb-1.5 block text-xs font-medium text-gray-400">
              Auto-Refresh
            </label>
            <select
              value={config.refreshInterval}
              onChange={(e) =>
                update("refreshInterval", Number(e.target.value))
              }
              className="w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm text-white focus:border-blue-500 focus:outline-none"
            >
              <option value={3000}>Every 3 seconds</option>
              <option value={5000}>Every 5 seconds</option>
              <option value={10000}>Every 10 seconds</option>
              <option value={30000}>Every 30 seconds</option>
              <option value={60000}>Every 60 seconds</option>
            </select>
          </div>
        </div>

        <p className="mt-4 text-xs text-gray-600">
          Tip: For more advanced settings (thresholds, stock universe), edit{" "}
          <code className="rounded bg-gray-800 px-1 py-0.5 text-gray-400">
            backend/config.py
          </code>{" "}
          and restart the backend.
        </p>
      </div>
    </div>
  );
}
