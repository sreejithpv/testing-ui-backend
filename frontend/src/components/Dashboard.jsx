import { useState } from "react";
import { useStockData } from "../hooks/useStockData";
import StockTable from "./StockTable";

export default function Dashboard({ config }) {
  const { data, loading, error, lastUpdated, refresh, countdown } =
    useStockData(config);

  return (
    <div className="space-y-4">
      {/* ── Status Bar ── */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-4 text-sm">
          {/* Live indicator */}
          <div className="flex items-center gap-1.5">
            <span className="animate-pulse-dot inline-block h-2 w-2 rounded-full bg-emerald-400" />
            <span className="text-gray-400">Live</span>
          </div>

          {/* Scanned count */}
          {data.meta?.total_scanned > 0 && (
            <span className="text-gray-500">
              {data.meta.total_scanned} stocks scanned
              {data.meta.scan_time !== undefined && (
                <> in {data.meta.scan_time}s</>
              )}
            </span>
          )}

          {/* Last updated */}
          {lastUpdated && (
            <span className="text-gray-500">
              Updated {lastUpdated.toLocaleTimeString()}
            </span>
          )}
        </div>

        <div className="flex items-center gap-3">
          {/* Next refresh countdown */}
          <span className="text-xs text-gray-600">
            Next refresh in {countdown}s
          </span>

          {/* Refresh button */}
          <button
            onClick={refresh}
            disabled={loading}
            className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-500 disabled:opacity-50"
          >
            <svg
              className={`h-4 w-4 ${loading ? "animate-spin" : ""}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
            Refresh
          </button>
        </div>
      </div>

      {/* ── Error Message ── */}
      {error && (
        <div className="rounded-lg border border-red-800 bg-red-950/50 px-4 py-3 text-sm text-red-300">
          <strong>Error:</strong> {error}
          <p className="mt-1 text-red-400/70">
            Make sure the backend is running on port 8000.
          </p>
        </div>
      )}

      {/* ── Tabs + Stock Tables ── */}
      {(() => {
        const tabs = [
          {
            id: "breakouts",
            icon: "🚀",
            label: "Breakout Candidates",
            color: "blue",
            desc: "Upward momentum — stocks breaking out of consolidation",
            stocks: data.breakouts,
            type: "breakout",
          },
          {
            id: "breakdowns",
            icon: "📉",
            label: "Breakdown Candidates",
            color: "orange",
            desc: "Downward momentum — stocks breaking down through support",
            stocks: data.breakdowns,
            type: "breakout",
          },
          {
            id: "bullish",
            icon: "▲",
            label: "Bullish Reversals",
            color: "emerald",
            desc: "Was falling, now turning UP — potential bounce / buy signal",
            stocks: data.bullish_reversals,
            type: "reversal",
          },
          {
            id: "bearish",
            icon: "▼",
            label: "Bearish Reversals",
            color: "red",
            desc: "Was rising, now turning DOWN — potential drop / sell signal",
            stocks: data.bearish_reversals,
            type: "reversal",
          },
        ];

        const colorMap = {
          blue: {
            active: "border-blue-400 text-blue-400",
            badge: "bg-blue-500/20 text-blue-400",
            tagBg: "bg-blue-500/10",
            tagText: "text-blue-400",
          },
          orange: {
            active: "border-orange-400 text-orange-400",
            badge: "bg-orange-500/20 text-orange-400",
            tagBg: "bg-orange-500/10",
            tagText: "text-orange-400",
          },
          emerald: {
            active: "border-emerald-400 text-emerald-400",
            badge: "bg-emerald-500/20 text-emerald-400",
            tagBg: "bg-emerald-500/10",
            tagText: "text-emerald-400",
          },
          red: {
            active: "border-red-400 text-red-400",
            badge: "bg-red-500/20 text-red-400",
            tagBg: "bg-red-500/10",
            tagText: "text-red-400",
          },
        };

        const [activeTab, setActiveTab] = useState("breakouts");
        const active = tabs.find((t) => t.id === activeTab);
        const cm = colorMap[active.color];

        return (
          <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-card)]">
            {/* Tab bar */}
            <div className="flex items-center gap-0 border-b border-[var(--color-border)] px-2">
              {tabs.map((tab) => {
                const isActive = activeTab === tab.id;
                const tcm = colorMap[tab.color];
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`flex items-center gap-1.5 px-4 py-3 text-sm font-medium transition-colors border-b-2 ${
                      isActive
                        ? `${tcm.active}`
                        : "border-transparent text-gray-500 hover:text-gray-300"
                    }`}
                  >
                    <span>{tab.icon}</span>
                    <span>{tab.label}</span>
                    {tab.stocks?.length > 0 && (
                      <span
                        className={`ml-1 rounded-full px-1.5 py-0.5 text-xs font-semibold ${
                          isActive ? tcm.badge : "bg-gray-800 text-gray-500"
                        }`}
                      >
                        {tab.stocks.length}
                      </span>
                    )}
                  </button>
                );
              })}
              <div className="ml-auto pr-2">
                <span
                  className={`rounded-full ${cm.tagBg} px-2.5 py-0.5 text-xs font-medium ${cm.tagText}`}
                >
                  {config.timeframe} chart
                </span>
              </div>
            </div>

            {/* Description */}
            <div className="px-5 py-2">
              <p className="text-xs text-gray-500">{active.desc}</p>
            </div>

            {/* Table */}
            <StockTable
              stocks={active.stocks}
              type={active.type}
              loading={loading}
            />
          </div>
        );
      })()}
    </div>
  );
}
