import { cn } from "@/lib/cn";
import { SEVERITY_LABEL, STATUS_LABEL, type DisplayStatus } from "@/lib/format";
import type { Severity } from "@/types";

const STATUS_STYLE: Record<DisplayStatus, string> = {
  up: "bg-up-tint text-up",
  degraded: "bg-degraded-tint text-degraded",
  down: "bg-down-tint text-down",
  unknown: "bg-hover text-subtle",
  paused: "bg-hover text-subtle",
};

const STATUS_DOT: Record<DisplayStatus, string> = {
  up: "bg-up",
  degraded: "bg-degraded",
  down: "bg-down",
  unknown: "bg-muted",
  paused: "bg-muted",
};

export function StatusBadge({ status }: { status: DisplayStatus }) {
  return (
    <span className={cn("inline-flex h-[22px] shrink-0 items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 text-xs font-medium", STATUS_STYLE[status])}>
      <span aria-hidden="true" className={cn("size-1.5 rounded-full", STATUS_DOT[status])} />
      {STATUS_LABEL[status]}
    </span>
  );
}

const SEVERITY_STYLE: Record<Severity, string> = {
  low: "bg-hover text-subtle",
  medium: "bg-degraded-tint text-degraded",
  high: "bg-down-tint text-down",
  critical: "bg-down text-on-down",
};

export function SeverityBadge({ severity }: { severity: Severity }) {
  return (
    <span className={cn("inline-flex h-[22px] shrink-0 items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 text-xs font-medium", SEVERITY_STYLE[severity])}>
      <span aria-hidden="true" className="size-1.5 rounded-full bg-current" />
      {SEVERITY_LABEL[severity]}
    </span>
  );
}
