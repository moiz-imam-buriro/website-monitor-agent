import { CircleCheck, CircleAlert } from "lucide-react";
import { SeverityBadge } from "@/components/ui/Badge";
import { SiteIcon } from "@/components/ui/SiteIcon";
import { formatDuration, formatRelative } from "@/lib/format";
import type { Incident } from "@/types";

interface IncidentCardProps {
  incident: Incident;
  monitorUrl: string;
  onOpen: (id: number) => void;
}

export function IncidentCard({ incident, monitorUrl, onOpen }: IncidentCardProps) {
  const open = incident.status === "open";
  return (
    <li>
      <button
        type="button"
        onClick={() => onOpen(incident.id)}
        className="flex w-full min-w-0 flex-col gap-3 rounded-xl border border-line bg-card p-4 text-left transition-colors duration-150 hover:bg-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent sm:p-5"
      >
        <div className="flex min-w-0 items-center gap-3">
          <SiteIcon url={monitorUrl} name={incident.monitor_name} />
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-ink">{incident.monitor_name}</p>
            <p className="truncate text-xs text-subtle">Started {formatRelative(incident.started_at)}</p>
          </div>
          <SeverityBadge severity={incident.severity} />
        </div>
        <p className="line-clamp-2 break-words text-sm text-subtle">{incident.summary || "No summary yet."}</p>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-subtle">
          <span className={open ? "flex items-center gap-1.5 text-down" : "flex items-center gap-1.5 text-up"}>
            {open ? <CircleAlert size={14} aria-hidden="true" /> : <CircleCheck size={14} aria-hidden="true" />}
            {open ? "Open" : "Resolved"}
          </span>
          <span>Duration {formatDuration(incident.duration_minutes)}</span>
        </div>
      </button>
    </li>
  );
}
