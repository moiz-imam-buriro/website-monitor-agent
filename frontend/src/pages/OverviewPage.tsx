import { getAgentStatus, listIncidents, listMonitors } from "@/api";
import { StatusBanner } from "@/components/overview/StatusBanner";
import { SystemCard } from "@/components/overview/SystemCard";
import { ResponseSection } from "@/components/overview/ResponseSection";
import { WebsitesCard } from "@/components/overview/WebsitesCard";
import { OpenIncidentsCard } from "@/components/overview/OpenIncidentsCard";
import { ErrorNotice, ResourceView } from "@/components/ui/ErrorNotice";
import { MetricTile, PageHeader } from "@/components/ui/Layout";
import { usePolling } from "@/hooks/usePolling";
import type { AgentStatus } from "@/types";

function StatusTiles({ status }: { status: AgentStatus }) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-4">
      <MetricTile label="Websites" value={status.monitors_total} />
      <MetricTile label="Up" value={status.monitors_up} tone="up" />
      <MetricTile label="Down" value={status.monitors_down} tone={status.monitors_down > 0 ? "down" : "neutral"} />
      <MetricTile label="Open incidents" value={status.open_incidents} tone={status.open_incidents > 0 ? "down" : "neutral"} />
    </div>
  );
}

export function OverviewPage() {
  const agent = usePolling("agent-status", (signal) => getAgentStatus(signal));
  const monitors = usePolling("monitors", (signal) => listMonitors(signal));
  const incidents = usePolling("incidents-open", (signal) => listIncidents({ status: "open", limit: 5 }, signal));

  return (
    <div className="flex min-w-0 flex-col gap-6">
      <PageHeader title="Overview" />

      <ResourceView
        state={agent}
        skeleton={<div className="grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-4"><div className="h-[104px] animate-pulse rounded-xl bg-hover" /><div className="h-[104px] animate-pulse rounded-xl bg-hover" /><div className="h-[104px] animate-pulse rounded-xl bg-hover" /><div className="h-[104px] animate-pulse rounded-xl bg-hover" /></div>}
        errorTitle="Could not load the system status."
      >
        {(status) => (
          <>
            <StatusBanner status={status} />
            <StatusTiles status={status} />
          </>
        )}
      </ResourceView>

      <div className="grid min-w-0 gap-4 xl:grid-cols-3">
        <div className="min-w-0 xl:col-span-2">
          <ResponseSection monitors={monitors} />
        </div>
        <SystemCard agent={agent} />
      </div>

      <div className="grid min-w-0 gap-4 lg:grid-cols-2">
        <WebsitesCard monitors={monitors} />
        <OpenIncidentsCard incidents={incidents} monitors={monitors.data ?? []} />
      </div>
    </div>
  );
}
