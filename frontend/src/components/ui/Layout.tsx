import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

export function Card({ className, children }: { className?: string; children: ReactNode }) {
  return <div className={cn("min-w-0 rounded-xl border border-line bg-card p-4 sm:p-5", className)}>{children}</div>;
}

export function CardHeader({ title, action }: { title: string; action?: ReactNode }) {
  return (
    <div className="mb-4 flex min-w-0 flex-wrap items-center justify-between gap-3">
      <h2 className="min-w-0 text-base font-medium leading-6 text-ink">{title}</h2>
      {action}
    </div>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div aria-hidden="true" className={cn("animate-pulse rounded-md bg-hover", className)} />;
}

export function EmptyState({ title, description, action }: { title: string; description?: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-2 px-4 py-10 text-center">
      <p className="text-sm font-medium text-ink">{title}</p>
      {description ? <p className="max-w-sm text-sm text-subtle">{description}</p> : null}
      {action ? <div className="mt-3">{action}</div> : null}
    </div>
  );
}

export function MetricTile({ label, value, tone = "neutral" }: { label: string; value: number | string; tone?: "up" | "down" | "neutral" }) {
  return (
    <div className="min-w-0 rounded-xl border border-line bg-card p-4 sm:p-5">
      <p className="text-xs text-subtle">{label}</p>
      <p className={cn("mt-2 truncate text-2xl font-medium leading-8 tabular-nums", tone === "up" ? "text-up" : tone === "down" ? "text-down" : "text-ink")}>
        {value}
      </p>
    </div>
  );
}

export function PageHeader({ title, actions }: { title: string; actions?: ReactNode }) {
  return (
    <header className="flex min-w-0 flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
      <h1 className="min-w-0 text-xl font-medium leading-7 text-ink sm:text-2xl sm:leading-8">{title}</h1>
      {actions ? <div className="flex flex-col gap-2 sm:flex-row sm:items-center [&>*]:w-full sm:[&>*]:w-auto">{actions}</div> : null}
    </header>
  );
}

export function Tabs<T extends string | number>({ label, tabs, value, onChange }: { label: string; tabs: { value: T; label: string }[]; value: T; onChange: (value: T) => void }) {
  return (
    <div role="tablist" aria-label={label} className="flex gap-6 overflow-x-auto border-b border-line">
      {tabs.map((tab) => {
        const active = tab.value === value;
        return (
          <button
            key={tab.value}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => onChange(tab.value)}
            className={cn(
              "-mb-px h-10 shrink-0 border-b-2 text-sm transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent",
              active ? "border-accent font-medium text-ink" : "border-transparent text-subtle hover:text-ink",
            )}
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}
