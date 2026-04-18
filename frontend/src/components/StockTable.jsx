/**
 * StockTable — Displays stocks with trading indicators and action levels.
 *
 * Columns:
 *  #  | Ticker | Action | Price | % Change | Entry/SL/TP | Vol | RSI | MACD | EMA | VWAP | Score | Signals
 *
 * Color coding:
 *  - Green for bullish / buy
 *  - Red for bearish / sell
 *  - Score uses a color gradient from gray → green/blue
 */

import { useState, useMemo } from "react";

function formatVolume(vol) {
  if (vol >= 1_000_000) return (vol / 1_000_000).toFixed(1) + "M";
  if (vol >= 1_000) return (vol / 1_000).toFixed(1) + "K";
  return vol.toString();
}

function formatPrice(p) {
  if (p == null) return "—";
  return p >= 100 ? p.toFixed(0) : p >= 1 ? p.toFixed(2) : p.toFixed(4);
}

function ScoreBadge({ score, type }) {
  let color = "text-gray-500 bg-gray-800";
  if (score >= 60) color = "text-emerald-300 bg-emerald-900/40";
  else if (score >= 40) color = "text-blue-300 bg-blue-900/40";
  else if (score >= 20) color = "text-yellow-300 bg-yellow-900/30";
  return (
    <span
      className={`inline-block rounded-md px-2 py-0.5 text-xs font-semibold ${color}`}
    >
      {score}
    </span>
  );
}

function ActionBadge({ action }) {
  const styles = {
    "Strong Buy":  "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
    "Buy":         "bg-emerald-900/30 text-emerald-400 border-emerald-500/20",
    "Hold":        "bg-gray-800 text-gray-400 border-gray-700",
    "Sell":        "bg-red-900/30 text-red-400 border-red-500/20",
    "Strong Sell": "bg-red-500/20 text-red-300 border-red-500/30",
  };
  return (
    <span className={`inline-block whitespace-nowrap rounded-md border px-2 py-0.5 text-xs font-bold ${styles[action] || styles["Hold"]}`}>
      {action}
    </span>
  );
}

function TrendArrow({ direction, label }) {
  if (direction === "bullish" || direction === "above") {
    return <span className="text-emerald-400" title={label}>▲</span>;
  }
  if (direction === "bearish" || direction === "below") {
    return <span className="text-red-400" title={label}>▼</span>;
  }
  return <span className="text-gray-600" title={label}>—</span>;
}



function LoadingSkeleton() {
  return (
    <div className="space-y-2 p-4">
      {[...Array(6)].map((_, i) => (
        <div
          key={i}
          className="h-10 animate-pulse rounded-lg bg-gray-800/50"
          style={{ animationDelay: `${i * 0.1}s` }}
        />
      ))}
    </div>
  );
}

function EmptyState({ type }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <span className="text-3xl">{type === "breakout" ? "📊" : "🔍"}</span>
      <p className="mt-2 text-sm text-gray-500">
        No {type === "breakout" ? "breakout candidates" : "trend reversals"}{" "}
        found
      </p>
      <p className="mt-1 text-xs text-gray-600">
        Market may be closed, or no stocks match the current thresholds
      </p>
    </div>
  );
}

export default function StockTable({ stocks = [], type, loading }) {
  if (loading && stocks.length === 0) return <LoadingSkeleton />;
  if (!stocks.length) return <EmptyState type={type} />;

  const scoreKey = type === "breakout" ? "breakout_score" : "reversal_score";
  const signalsKey =
    type === "breakout" ? "breakout_signals" : "reversal_signals";

  const [sortCol, setSortCol] = useState(null);
  const [sortDir, setSortDir] = useState("desc");

  const handleSort = (col) => {
    if (sortCol === col) {
      setSortDir((d) => (d === "desc" ? "asc" : "desc"));
    } else {
      setSortCol(col);
      setSortDir("desc");
    }
  };

  const sortedStocks = useMemo(() => {
    if (!sortCol) return stocks;
    const copy = [...stocks];
    copy.sort((a, b) => {
      let va = sortCol === "score" ? a[scoreKey] : a[sortCol];
      let vb = sortCol === "score" ? b[scoreKey] : b[sortCol];
      if (va == null) va = -Infinity;
      if (vb == null) vb = -Infinity;
      if (typeof va === "string") return sortDir === "asc" ? va.localeCompare(vb) : vb.localeCompare(va);
      return sortDir === "asc" ? va - vb : vb - va;
    });
    return copy;
  }, [stocks, sortCol, sortDir, scoreKey]);

  const SortIcon = ({ col }) => {
    if (sortCol !== col) return <span className="ml-1 text-gray-700">⇅</span>;
    return <span className="ml-1 text-blue-400">{sortDir === "asc" ? "↑" : "↓"}</span>;
  };

  const Th = ({ col, children, className = "" }) => (
    <th
      className={`px-3 py-2.5 font-medium cursor-pointer select-none hover:text-gray-300 transition-colors ${className}`}
      onClick={() => handleSort(col)}
    >
      <span className="inline-flex items-center gap-0.5">{children}<SortIcon col={col} /></span>
    </th>
  );

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[var(--color-border)] text-left text-xs uppercase tracking-wider text-gray-500">
            <th className="px-3 py-2.5 font-medium">#</th>
            <Th col="ticker">Ticker</Th>
            <Th col="trade_action" className="text-center">Action</Th>
            <Th col="price" className="text-right">Price</Th>
            <Th col="pct_change" className="text-right">% Chg</Th>
            <th className="px-3 py-2.5 font-medium text-right">Entry / SL / TP</th>
            <Th col="risk_reward" className="text-right">R:R</Th>
            <Th col="volume" className="text-right">Vol</Th>
            <Th col="rsi" className="text-right">RSI</Th>
            <Th col="macd_direction" className="text-center">MACD</Th>
            <Th col="ema_trend" className="text-center">EMA</Th>
            <Th col="vwap_signal" className="text-center">VWAP</Th>
            <Th col="score" className="text-center">Score</Th>
            <th className="px-3 py-2.5 font-medium">Signals</th>
          </tr>
        </thead>
        <tbody>
          {sortedStocks.map((stock, index) => (
            <tr
              key={stock.ticker}
              className="border-b border-[var(--color-border)]/50 transition-colors hover:bg-[var(--color-card-hover)]"
            >
              {/* Row number */}
              <td className="px-3 py-2.5 text-gray-600">{index + 1}</td>

              {/* Ticker */}
              <td className="px-3 py-2.5 font-semibold text-white">
                {stock.ticker}
              </td>

              {/* Trade Action */}
              <td className="px-3 py-2.5 text-center">
                <ActionBadge action={stock.trade_action || "Hold"} />
              </td>

              {/* Price */}
              <td className="px-3 py-2.5 text-right font-mono text-gray-300">
                ${formatPrice(stock.price)}
              </td>

              {/* Percentage Change */}
              <td
                className={`px-3 py-2.5 text-right font-mono font-semibold ${
                  stock.pct_change >= 0
                    ? "text-[var(--color-bull)]"
                    : "text-[var(--color-bear)]"
                }`}
              >
                {stock.pct_change > 0 ? "+" : ""}
                {stock.pct_change.toFixed(2)}%
              </td>

              {/* Entry / Stop-Loss / Target */}
              <td className="px-3 py-2.5 text-right font-mono text-xs leading-relaxed">
                <span className="text-gray-300">{formatPrice(stock.price)}</span>
                <span className="text-gray-600"> / </span>
                <span className="text-red-400">{formatPrice(stock.stop_loss)}</span>
                <span className="text-gray-600"> / </span>
                <span className="text-emerald-400">{formatPrice(stock.target)}</span>
              </td>

              {/* Risk:Reward */}
              <td className={`px-3 py-2.5 text-right font-mono text-xs ${
                stock.risk_reward >= 2 ? "text-emerald-400" : stock.risk_reward >= 1 ? "text-yellow-400" : "text-red-400"
              }`}>
                {stock.risk_reward ? `1:${stock.risk_reward}` : "—"}
              </td>

              {/* Volume */}
              <td className="px-3 py-2.5 text-right text-gray-400">
                {formatVolume(stock.volume)}
                {stock.volume_ratio > 1.5 && (
                  <span className="ml-1 text-xs text-yellow-500">
                    {stock.volume_ratio.toFixed(1)}x
                  </span>
                )}
              </td>

              {/* RSI */}
              <td
                className={`px-3 py-2.5 text-right font-mono ${
                  stock.rsi < 30
                    ? "text-[var(--color-bull)]"
                    : stock.rsi > 70
                      ? "text-[var(--color-bear)]"
                      : "text-gray-400"
                }`}
              >
                {stock.rsi.toFixed(0)}
              </td>

              {/* MACD direction */}
              <td className="px-3 py-2.5 text-center">
                <TrendArrow direction={stock.macd_direction} label={`MACD: ${stock.macd_direction}`} />
              </td>

              {/* EMA trend */}
              <td className="px-3 py-2.5 text-center">
                <TrendArrow direction={stock.ema_trend} label={`EMA 9: ${stock.ema_9} / EMA 21: ${stock.ema_21}`} />
              </td>

              {/* VWAP */}
              <td className="px-3 py-2.5 text-center">
                <TrendArrow direction={stock.vwap_signal} label={`VWAP: $${stock.vwap}`} />
              </td>

              {/* Score */}
              <td className="px-3 py-2.5 text-center">
                <ScoreBadge score={stock[scoreKey]} type={type} />
              </td>

              {/* Signals */}
              <td className="px-3 py-2.5">
                <div className="flex flex-wrap gap-1">
                  {stock[signalsKey]?.map((signal, i) => (
                    <span
                      key={i}
                      className="rounded bg-gray-800 px-1.5 py-0.5 text-xs text-gray-400"
                    >
                      {signal}
                    </span>
                  ))}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
