import type { ReactNode } from "react";
import { getIncident } from "@/api";
import { SeverityBadge } from "@/components/ui/Badge";
import { ErrorCard } from "@/components/ui/ErrorNotice";
import { Drawer } from "@/components/ui/Overlays";
import { SiteIcon } from "@/components/ui/SiteIcon";
import { Skeleton } from "@/components/ui/Layout";
import { usePolling } from "@/hooks/usePolling";
import { formatDuration, formatExact } from "@/lib/format";
import type { Incident } from "@/types";

interface IncidentDrawerProps {
  incidentId: number;
  monitorUrlFor: (monitorId: number) => string;
  onClose: () => void;
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="flex min-w-0 flex-col gap-2">
      <h3 className="text-sm font-medium text-ink">{title}</h3>
      {children}
    </section>
  );
}

function BulletList({ items }: { items: string[] }) {
  if (items.length === 0) return <p className="text-sm text-muted">None listed.</p>;
  return (
    <ul className="flex list-disc flex-col gap-1.5 pl-5 text-sm text-ink marker:text-muted">
      {items.map((item, index) => (
        <li key={`${index}-${item}`} className="break-words">{item}</li>
      ))}
    </ul>
  );
}

function IncidentBody({ incident }: { incident: Incident }) {
  return (
    <div className="flex min-w-0 flex-col gap-6">
      {incident.analyzed ? null : (
        <p className="rounded-lg border border-line bg-hover p-3 text-sm text-subtle">
          The AI has not written an explanation for this incident yet.
        </p>
      )}
      <Section title="Summary">
        <p className="break-words text-sm text-ink">{incident.summary || "No summary yet."}</p>
      </Section>
      <Section title="Probable cause">
        <p className="break-words text-sm text-ink">{incident.probable_cause || "Not determined yet."}</p>
      </Section>
      <Section title="Affected areas">
        <BulletList items={incident.affected} />
      </Section>
      <Section title="Suggested next steps">
        <BulletList items={incident.suggestions} />
      </Section>
      <Section title="Timeline">
        <dl className="flex flex-col text-sm">
          <div className="flex justify-between gap-3 border-b border-line py-2.5">
            <dt className="text-subtle">Started</dt>
            <dd className="text-right text-ink">{formatExact(incident.started_at)}</dd>
          </div>
          <div className="flex justify-between gap-3 border-b border-line py-2.5">
            <dt className="text-subtle">Resolved</dt>
            <dd className="text-right text-ink">{incident.resolved_at ? formatExact(incident.resolved_at) : "Still open"}</dd>
          </div>
          <div className="flex justify-between gap-3 border-b border-line py-2.5">
            <dt className="text-subtle">Duration</dt>
            <dd className="text-right text-ink">{formatDuration(incident.duration_minutes)}</dd>
          </div>
          <div className="flex justify-between gap-3 py-2.5">
            <dt className="text-subtle">Alert email</dt>
            <dd className="text-right text-ink">{incident.alert_sent ? "Sent" : "Not sent"}</dd>
          </div>
        </dl>
      </Section>
    </div>
  );
}

export function IncidentDrawer({ incidentId, monitorUrlFor, onClose }: IncidentDrawerProps) {
  const incident = usePolling(`incident-${incidentId}`, (signal) => getIncident(incidentId, signal));

  const title =
    incident.data === null ? (
      <span className="text-base font-medium text-ink">Incident</span>
    ) : (
      <div className="flex min-w-0 items-center gap-3">
        <SiteIcon url={monitorUrlFor(incident.data.monitor_id)} name={incident.data.monitor_name} />
        <div className="min-w-0">
          <p className="truncate text-base font-medium text-ink">{incident.data.monitor_name}</p>
          <div className="mt-1 flex items-center gap-2">
            <SeverityBadge severity={incident.data.severity} />
            <span className="text-xs text-subtle">{incident.data.status === "open" ? "Open" : "Resolved"}</span>
          </div>
        </div>
      </div>
    );

  return (
    <Drawer title={title} onClose={onClose}>
      {incident.data === null ? (
        incident.error ? (
          <ErrorCard title="Could not load this incident." error={incident.error} onRetry={incident.refresh} />
        ) : (
          <div className="flex flex-col gap-4">
            <Skeleton className="h-6 w-1/2" />
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-40 w-full" />
          </div>
        )
      ) : (
        <IncidentBody incident={incident.data} />
      )}
    </Drawer>
  );
}
