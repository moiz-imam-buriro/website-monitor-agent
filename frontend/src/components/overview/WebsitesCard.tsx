import { Link } from "react-router-dom";
import { ChevronRight } from "lucide-react";
import { Card, CardHeader, EmptyState, Skeleton } from "@/components/ui/Layout";
import { ResourceView } from "@/components/ui/ErrorNotice";
import { SiteIcon } from "@/components/ui/SiteIcon";
import { StatusBadge } from "@/components/ui/Badge";
import type { PollResult } from "@/hooks/usePolling";
import { displayStatus, formatRelative, hostnameOf } from "@/lib/format";
import type { Monitor } from "@/types";

interface WebsitesCardProps {
  monitors: PollResult<Monitor[]>;
}

export function WebsitesCard({ monitors }: WebsitesCardProps) {
  return (
    <Card>
      <CardHeader
        title="Websites"
        action={<Link to="/websites" className="text-sm font-medium text-accent hover:underline">View all</Link>}
      />
      <ResourceView state={monitors} skeleton={<Skeleton className="h-[200px] w-full" />} errorTitle="Could not load your websites.">
        {(list) =>
          list.length === 0 ? (
            <EmptyState title="No websites yet" description="Add your first website from the Websites page." />
          ) : (
            <ul className="-mx-2 flex flex-col">
              {list.map((monitor) => (
                <li key={monitor.id}>
                  <Link
                    to={`/websites?site=${monitor.id}`}
                    className="group flex min-w-0 items-center gap-3 rounded-lg px-2 py-3 transition-colors duration-150 hover:bg-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                  >
                    <SiteIcon url={monitor.url} name={monitor.name} />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-medium text-ink">{monitor.name}</span>
                      <span className="block truncate text-xs text-subtle">
                        {hostnameOf(monitor.url) || monitor.url} | {formatRelative(monitor.last_checked_at)}
                      </span>
                    </span>
                    <StatusBadge status={displayStatus(monitor)} />
                    <ChevronRight size={16} aria-hidden="true" className="hidden shrink-0 text-muted sm:block" />
                  </Link>
                </li>
              ))}
            </ul>
          )
        }
      </ResourceView>
    </Card>
  );
}
