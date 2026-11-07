import { useCallback, useEffect, useRef, useState } from "react";
import { isAbortError } from "@/api";

const REFRESH_INTERVAL_MS = 30_000;

interface PollState<T> {
  key: string;
  data: T | null;
  error: unknown;
}

export interface PollResult<T> {
  data: T | null;
  error: unknown;
  refresh: () => void;
}

export function usePolling<T>(
  key: string,
  load: (signal: AbortSignal) => Promise<T>,
  intervalMs: number = REFRESH_INTERVAL_MS,
): PollResult<T> {
  const [state, setState] = useState<PollState<T>>({ key, data: null, error: null });
  const [nonce, setNonce] = useState(0);
  const loadRef = useRef(load);

  useEffect(() => {
    loadRef.current = load;
  });

  useEffect(() => {
    let controller: AbortController | undefined;

    const run = () => {
      controller?.abort();
      const current = new AbortController();
      controller = current;
      loadRef.current(current.signal).then(
        (data) => {
          if (!current.signal.aborted) setState({ key, data, error: null });
        },
        (error: unknown) => {
          if (current.signal.aborted || isAbortError(error)) return;
          setState((prev) => ({ key, data: prev.key === key ? prev.data : null, error }));
        },
      );
    };

    const canRun = () => document.visibilityState === "visible" && navigator.onLine;
    const onVisibleOrOnline = () => {
      if (canRun()) run();
    };

    run();
    const timer = window.setInterval(onVisibleOrOnline, intervalMs);
    document.addEventListener("visibilitychange", onVisibleOrOnline);
    window.addEventListener("online", onVisibleOrOnline);

    return () => {
      controller?.abort();
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisibleOrOnline);
      window.removeEventListener("online", onVisibleOrOnline);
    };
  }, [key, intervalMs, nonce]);

  const refresh = useCallback(() => setNonce((n) => n + 1), []);
  const sameKey = state.key === key;
  return {
    data: sameKey ? state.data : null,
    error: sameKey ? state.error : null,
    refresh,
  };
}
