import { useCallback } from "react";
import { useSearchParams } from "react-router-dom";

export function useIdParam(name: string): [number | null, (id: number | null) => void] {
  const [params, setParams] = useSearchParams();
  const raw = params.get(name);
  const id = raw && /^\d+$/.test(raw) ? Number(raw) : null;

  const setId = useCallback(
    (next: number | null) => {
      setParams((current) => {
        const updated = new URLSearchParams(current);
        if (next === null) updated.delete(name);
        else updated.set(name, String(next));
        return updated;
      });
    },
    [name, setParams],
  );

  return [id, setId];
}
