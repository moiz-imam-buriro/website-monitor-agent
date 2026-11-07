import { useEffect } from "react";
import { CircleAlert, CircleCheck, X } from "lucide-react";
import type { ToastItem } from "@/hooks/useToast";
import { TechnicalDetails } from "@/components/ui/ErrorNotice";

const SUCCESS_MS = 4000;
const ERROR_MS = 8000;

function ToastCard({ toast, onDismiss }: { toast: ToastItem; onDismiss: (id: number) => void }) {
  useEffect(() => {
    const timer = window.setTimeout(() => onDismiss(toast.id), toast.tone === "error" ? ERROR_MS : SUCCESS_MS);
    return () => window.clearTimeout(timer);
  }, [onDismiss, toast.id, toast.tone]);

  const isError = toast.tone === "error";
  return (
    <div role={isError ? "alert" : "status"} className="flex min-w-0 gap-3 rounded-xl border border-line bg-card p-4">
      {isError ? (
        <CircleAlert size={16} aria-hidden="true" className="mt-0.5 shrink-0 text-down" />
      ) : (
        <CircleCheck size={16} aria-hidden="true" className="mt-0.5 shrink-0 text-up" />
      )}
      <div className="min-w-0 flex-1">
        <p className="break-words text-sm text-ink">{toast.message}</p>
        {toast.technical ? <TechnicalDetails info={toast.technical} /> : null}
      </div>
      <button
        type="button"
        aria-label="Dismiss notification"
        onClick={() => onDismiss(toast.id)}
        className="ctl-square -m-2 inline-flex shrink-0 items-center justify-center rounded-lg text-subtle hover:bg-hover hover:text-ink"
      >
        <X size={16} aria-hidden="true" />
      </button>
    </div>
  );
}

export function ToastRegion({ toasts, onDismiss }: { toasts: ToastItem[]; onDismiss: (id: number) => void }) {
  if (toasts.length === 0) return null;
  return (
    <div className="pointer-events-none fixed inset-x-4 bottom-[max(16px,env(safe-area-inset-bottom))] z-[70] flex flex-col gap-2 sm:left-auto sm:right-4 sm:w-[360px]">
      {toasts.map((toast) => (
        <div key={toast.id} className="pointer-events-auto">
          <ToastCard toast={toast} onDismiss={onDismiss} />
        </div>
      ))}
    </div>
  );
}
