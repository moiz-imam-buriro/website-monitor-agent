import { useState, type ReactNode } from "react";
import { ChevronDown, CircleAlert, LoaderCircle, RefreshCw } from "lucide-react";
import { describeError, type TechnicalInfo } from "@/api";
import { cn } from "@/lib/cn";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Layout";
import type { PollResult } from "@/hooks/usePolling";

export function TechnicalDetails({ info }: { info: TechnicalInfo }) {
  const [open, setOpen] = useState(false);
  const rows: [string, string][] = [
    ["Method", info.method],
    ["URL", info.url],
    ["Status", info.status !== null ? String(info.status) : (info.networkError ?? "No response")],
    ["Response", info.responseText ?? "(empty)"],
  ];
  return (
    <div className="mt-2">
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((current) => !current)}
        className="inline-flex items-center gap-1 text-xs font-medium text-accent hover:underline"
      >
        {open ? "Hide technical details" : "Technical details"}
        <ChevronDown size={14} aria-hidden="true" className={cn("transition-transform duration-150", open && "rotate-180")} />
      </button>
      {open ? (
        <dl className="mt-2 grid gap-2 rounded-lg border border-line bg-page p-3 font-mono text-xs text-subtle">
          {rows.map(([label, value]) => (
            <div key={label} className="grid min-w-0 gap-0.5">
              <dt className="font-sans text-muted">{label}</dt>
              <dd className="min-w-0 break-all text-ink">{value}</dd>
            </div>
          ))}
        </dl>
      ) : null}
    </div>
  );
}

export function ErrorNotice({ error }: { error: unknown }) {
  const { message, technical } = describeError(error);
  return (
    <div role="alert" className="flex min-w-0 gap-2 text-sm text-down">
      <CircleAlert size={16} aria-hidden="true" className="mt-0.5 shrink-0" />
      <div className="min-w-0 flex-1">
        <p className="break-words">{message}</p>
        {technical ? <TechnicalDetails info={technical} /> : null}
      </div>
    </div>
  );
}

export function ErrorCard({ title, error, onRetry }: { title: string; error: unknown; onRetry: () => void }) {
  return (
    <Card>
      <p className="mb-3 text-sm font-medium text-ink">{title}</p>
      <ErrorNotice error={error} />
      <div className="mt-4">
        <Button variant="secondary" icon={<RefreshCw size={16} aria-hidden="true" />} onClick={onRetry}>
          Retry
        </Button>
      </div>
    </Card>
  );
}

interface ResourceViewProps<T> {
  state: PollResult<T>;
  skeleton: ReactNode;
  errorTitle: string;
  children: (data: T) => ReactNode;
}

export function ResourceView<T>({ state, skeleton, errorTitle, children }: ResourceViewProps<T>) {
  if (state.data === null) {
    if (state.error) return <ErrorCard title={errorTitle} error={state.error} onRetry={state.refresh} />;
    return <>{skeleton}</>;
  }
  return (
    <div className="flex min-w-0 flex-col gap-4">
      {state.error ? (
        <p className="flex items-center gap-2 text-xs text-muted">
          <LoaderCircle size={12} aria-hidden="true" className="animate-spin" />
          Could not refresh. Retrying.
        </p>
      ) : null}
      {children(state.data)}
    </div>
  );
}
