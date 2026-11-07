import { useState, type ReactNode } from "react";
import { LoaderCircle, Mail, Pencil, RefreshCw, Trash2 } from "lucide-react";
import { getMonitor } from "@/api";
import { Button } from "@/components/ui/Button";
import { StatusBadge } from "@/components/ui/Badge";
import { ErrorCard } from "@/components/ui/ErrorNotice";
import { Drawer } from "@/components/ui/Overlays";
import { SiteIcon } from "@/components/ui/SiteIcon";
import { Skeleton, Tabs } from "@/components/ui/Layout";
import { MonitorHistory } from "@/components/monitors/MonitorHistory";
import type { MonitorActions } from "@/components/monitors/MonitorList";
import { usePolling } from "@/hooks/usePolling";
import { displayStatus, formatExact, formatInterval, formatRelative } from "@/lib/format";
import type { Monitor } from "@/types";

const RANGES = [
  { value: 24, label: "24 hours" },
  { value: 168, label: "7 days" },
];

interface WebsiteDrawerProps {
  monitorId: number;
  actions: MonitorActions;
  busy: boolean;
  onClose: () => void;
}

function Detail({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex min-w-0 flex-col gap-1 border-b border-line py-3 last:border-b-0">
      <dt className="text-xs text-subtle">{label}</dt>
      <dd className="min-w-0 break-words text-sm text-ink">{children}</dd>
    </div>
  );
}

function MonitorDetails({ monitor }: { monitor: Monitor }) {
  return (
    <dl className="flex flex-col">
      <Detail label="Address"><a href={monitor.url} target="_blank" rel="noreferrer" className="text-accent hover:underline">{monitor.url}</a></Detail>
      <Detail label="Pages checked">{monitor.routes.length > 0 ? monitor.routes.join(", ") : "None"}</Detail>
      <Detail label="API endpoints">{monitor.api_endpoints.length > 0 ? monitor.api_endpoints.join(", ") : "None"}</Detail>
      <Detail label="Alert email">{monitor.alert_email}</Detail>
      <Detail label="Check interval">{formatInterval(monitor.interval_minutes)}</Detail>
      <Detail label="Last checked">{monitor.last_checked_at ? `${formatRelative(monitor.last_checked_at)} (${formatExact(monitor.last_checked_at)})` : "Never"}</Detail>
      <Detail label="Added">{formatExact(monitor.created_at)}</Detail>
    </dl>
  );
}

export function WebsiteDrawer({ monitorId, actions, busy, onClose }: WebsiteDrawerProps) {
  const monitor = usePolling(`monitor-${monitorId}`, (signal) => getMonitor(monitorId, signal));
  const [hours, setHours] = useState(24);

  if (monitor.data === null) {
    return (
      <Drawer title={<span className="text-base font-medium text-ink">Website</span>} onClose={onClose}>
        {monitor.error ? (
          <ErrorCard title="Could not load this website." error={monitor.error} onRetry={monitor.refresh} />
        ) : (
          <div className="flex flex-col gap-4">
            <Skeleton className="h-10 w-2/3" />
            <Skeleton className="h-[240px] w-full" />
          </div>
        )}
      </Drawer>
    );
  }

  const current = monitor.data;
  return (
    <Drawer
      title={
        <div className="flex min-w-0 items-center gap-3">
          <SiteIcon url={current.url} name={current.name} />
          <div className="min-w-0">
            <p className="truncate text-base font-medium text-ink">{current.name}</p>
            <div className="mt-1"><StatusBadge status={displayStatus(current)} /></div>
          </div>
        </div>
      }
      onClose={onClose}
      footer={
        <div className="flex flex-wrap gap-2">
          <Button variant="primary" icon={<Pencil size={16} aria-hidden="true" />} onClick={() => actions.onEdit(current)}>Edit</Button>
          <Button
            variant="secondary"
            disabled={busy}
            icon={busy ? <LoaderCircle size={16} aria-hidden="true" className="animate-spin" /> : <RefreshCw size={16} aria-hidden="true" />}
            onClick={() => actions.onCheck(current)}
          >
            Check now
          </Button>
          <Button variant="secondary" icon={<Mail size={16} aria-hidden="true" />} onClick={() => actions.onTestEmail(current)}>Test email</Button>
          <Button variant="ghost" className="text-down" icon={<Trash2 size={16} aria-hidden="true" />} onClick={() => actions.onDelete(current)}>Delete</Button>
        </div>
      }
    >
      <div className="flex min-w-0 flex-col gap-6">
        <MonitorDetails monitor={current} />
        <section className="flex min-w-0 flex-col gap-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h3 className="text-sm font-medium text-ink">Response times</h3>
            <Tabs label="Time range" tabs={RANGES} value={hours} onChange={setHours} />
          </div>
          <MonitorHistory monitorId={current.id} hours={hours} />
        </section>
      </div>
    </Drawer>
  );
}
