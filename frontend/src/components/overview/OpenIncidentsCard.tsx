import { Link } from "react-router-dom";
import { Card, CardHeader, EmptyState, Skeleton } from "@/components/ui/Layout";
import { ResourceView } from "@/components/ui/ErrorNotice";
import { SeverityBadge } from "@/components/ui/Badge";
import { SiteIcon } from "@/components/ui/SiteIcon";
import type { PollResult } from "@/hooks/usePolling";
import { formatRelative } from "@/lib/format";
import type { Incident, Monitor } from "@/types";

interface OpenIncidentsCardProps {
  incidents: PollResult<Incident[]>;
  monitors: Monitor[];
}

export function OpenIncidentsCard({ incidents, monitors }: OpenIncidentsCardProps) {
  return (
    <Card>
      <CardHeader
        title="Open incidents"
        action={<Link to="/incidents?status=open" className="text-sm font-medium text-accent hover:underline">View all</Link>}
      />
      <ResourceView state={incidents} skeleton={<Skeleton className="h-[200px] w-full" />} errorTitle="Could not load the open incidents.">
        {(list) =>
          list.length === 0 ? (
            <EmptyState title="No open incidents" description="Every monitored website is currently healthy." />
          ) : (
            <ul className="-mx-2 flex flex-col">
              {list.map((incident) => {
                const monitor = monitors.find((item) => item.id === incident.monitor_id);
                return (
                  <li key={incident.id}>
                    <Link
                      to={`/incidents?incident=${incident.id}`}
                      className="flex min-w-0 items-center gap-3 rounded-lg px-2 py-3 transition-colors duration-150 hover:bg-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                    >
                      <SiteIcon url={monitor?.url ?? ""} name={incident.monitor_name} />
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm font-medium text-ink">{incident.monitor_name}</span>
                        <span className="block truncate text-xs text-subtle">Started {formatRelative(incident.started_at)}</span>
                      </span>
                      <SeverityBadge severity={incident.severity} />
                    </Link>
                  </li>
                );
              })}
            </ul>
          )
        }
      </ResourceView>
    </Card>
  );
}
