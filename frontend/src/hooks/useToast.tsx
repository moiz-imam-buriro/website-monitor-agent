import { createContext, useCallback, useContext, useMemo, useRef, useState, type ReactNode } from "react";
import { describeError, type TechnicalInfo } from "@/api";
import { ToastRegion } from "@/components/ui/ToastRegion";

export type ToastTone = "success" | "error";

export interface ToastItem {
  id: number;
  tone: ToastTone;
  message: string;
  technical: TechnicalInfo | null;
}

interface ToastContextValue {
  success: (message: string) => void;
  error: (error: unknown) => void;
  dismiss: (id: number) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const nextId = useRef(0);

  const add = useCallback((tone: ToastTone, message: string, technical: TechnicalInfo | null) => {
    nextId.current += 1;
    const item: ToastItem = { id: nextId.current, tone, message, technical };
    setToasts((current) => [...current, item]);
  }, []);

  const dismiss = useCallback((id: number) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);

  const value = useMemo<ToastContextValue>(
    () => ({
      success: (message) => add("success", message, null),
      error: (error) => {
        const described = describeError(error);
        add("error", described.message, described.technical);
      },
      dismiss,
    }),
    [add, dismiss],
  );

  return (
    <ToastContext.Provider value={value}>
      {children}
      <ToastRegion toasts={toasts} onDismiss={dismiss} />
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const context = useContext(ToastContext);
  if (!context) throw new Error("useToast must be used inside ToastProvider");
  return context;
}
