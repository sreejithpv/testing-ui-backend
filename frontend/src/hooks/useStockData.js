import { useState, useEffect, useCallback, useRef } from "react";

/**
 * Custom React hook that fetches stock scan data from the backend API.
 *
 * What it does:
 * - Fetches breakout + reversal data on mount
 * - Auto-refreshes every `config.refreshInterval` milliseconds
 * - Provides a manual refresh function
 * - Tracks loading/error state and last-updated time
 *
 * @param {object} config - { timeframe, sort_by, sort_order, max_results, refreshInterval }
 * @returns {{ data, loading, error, lastUpdated, refresh, countdown }}
 */
export function useStockData(config) {
  const [data, setData] = useState({
    breakouts: [],
    breakdowns: [],
    reversals: [],
    bullish_reversals: [],
    bearish_reversals: [],
    meta: {},
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [countdown, setCountdown] = useState(config.refreshInterval / 1000);
  const intervalRef = useRef(null);
  const countdownRef = useRef(null);

  const fetchData = useCallback(
    async (force = false) => {
      try {
        // Build URL query parameters from config
        const params = new URLSearchParams({
          timeframe: config.timeframe,
          sort_by: config.sort_by,
          sort_order: config.sort_order,
          max_results: config.max_results.toString(),
        });
        if (force) params.append("force", "1");

        const res = await fetch(`/api/scan?${params}`);

        if (!res.ok) {
          throw new Error(`API error: ${res.status} ${res.statusText}`);
        }

        const json = await res.json();
        setData(json);
        setLastUpdated(new Date());
        setError(null);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    },
    [config.timeframe, config.sort_by, config.sort_order, config.max_results]
  );

  // Auto-fetch on mount and when config changes
  useEffect(() => {
    setLoading(true);
    fetchData();

    // Set up periodic refresh
    intervalRef.current = setInterval(() => {
      fetchData();
    }, config.refreshInterval);

    return () => clearInterval(intervalRef.current);
  }, [fetchData, config.refreshInterval]);

  // Countdown timer (visual indicator of next refresh)
  useEffect(() => {
    setCountdown(config.refreshInterval / 1000);

    countdownRef.current = setInterval(() => {
      setCountdown((prev) => (prev <= 1 ? config.refreshInterval / 1000 : prev - 1));
    }, 1000);

    return () => clearInterval(countdownRef.current);
  }, [config.refreshInterval, lastUpdated]);

  // Manual refresh: bypass cache
  const refresh = useCallback(() => {
    setLoading(true);
    setCountdown(config.refreshInterval / 1000);
    fetchData(true);
  }, [fetchData, config.refreshInterval]);

  return { data, loading, error, lastUpdated, refresh, countdown };
}
