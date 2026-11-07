import { useReducer, useEffect, type ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { SESSION_EXPIRED_EVENT } from "@/api";
import { getSession } from "@/lib/session";

export function RequireAuth({ children }: { children: ReactNode }) {
  const location = useLocation();
  const [, rerender] = useReducer((count: number) => count + 1, 0);

  useEffect(() => {
    window.addEventListener(SESSION_EXPIRED_EVENT, rerender);
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, rerender);
  }, []);

  if (!getSession()) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return <>{children}</>;
}
