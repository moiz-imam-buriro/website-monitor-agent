import { useState } from "react";
import { listIncidents, listMonitors } from "@/api";
import { Button } from "@/components/ui/Button";
import { SelectField } from "@/components/ui/Fields";
import { ResourceView } from "@/components/ui/ErrorNotice";
import { EmptyState, PageHeader, Skeleton, Tabs } from "@/components/ui/Layout";
import { IncidentCard } from "@/components/incidents/IncidentCard";
import { IncidentDrawer } from "@/components/incidents/IncidentDrawer";
import { useIdParam } from "@/hooks/useIdParam";
import { usePolling } from "@/hooks/usePolling";
import type { Incident } from "@/types";

const PAGE_SIZE = 20;

type StatusTab = "all" | "open" | "resolved";

const TABS: { value: StatusTab; label: string }[] = [
  { value: "all", label: "All" },
  { value: "open", label: "Open" },
  { value: "resolved", label: "Resolved" },
];

export function IncidentsPage() {
  const monitors = usePolling("monitors", (signal) => listMonitors(signal));
  const [tab, setTab] = useState<StatusTab>(() => {
    const initial = new URLSearchParams(window.location.search).get("status");
    return initial === "open" || initial === "resolved" ? initial : "all";
  });
  const [monitorFilter, setMonitorFilter] = useState<number | null>(null);
  const [limit, setLimit] = useState(PAGE_SIZE);
  const [incidentId, setIncidentId] = useIdParam("incident");

  const status = tab === "all" ? undefined : tab;
  const incidents = usePolling(`incidents-${tab}-${monitorFilter ?? "all"}-${limit}`, (signal) =>
    listIncidents({ status, monitor_id: monitorFilter ?? undefined, limit }, signal),
  );

  const urlFor = (monitorId: number) => monitors.data?.find((item) => item.id === monitorId)?.url ?? "";

  const changeTab = (next: StatusTab) => {
    setTab(next);
    setLimit(PAGE_SIZE);
  };

  const changeMonitor = (value: string) => {
    setMonitorFilter(value === "" ? null : Number(value));
    setLimit(PAGE_SIZE);
  };

  const renderList = (list: Incident[]) => {
    if (list.length === 0) {
      return (
        <EmptyState
          title="No incidents here"
          description={tab === "open" ? "Nothing is down right now." : "No incidents match these filters."}
        />
      );
    }
    return (
      <div className="flex flex-col gap-3">
        <ul className="flex flex-col gap-3">
          {list.map((incident) => (
            <IncidentCard key={incident.id} incident={incident} monitorUrl={urlFor(incident.monitor_id)} onOpen={setIncidentId} />
          ))}
        </ul>
        {list.length >= limit ? (
          <div className="flex justify-center pt-2">
            <Button variant="secondary" onClick={() => setLimit((current) => current + PAGE_SIZE)}>Load more</Button>
          </div>
        ) : null}
      </div>
    );
  };

  return (
    <div className="flex min-w-0 flex-col gap-6">
      <PageHeader title="Incidents" />

      <div className="flex min-w-0 flex-col gap-4">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <Tabs label="Incident status" tabs={TABS} value={tab} onChange={changeTab} />
          <div className="w-full sm:w-64">
            <SelectField
              id="incident-website"
              label="Website"
              value={monitorFilter === null ? "" : String(monitorFilter)}
              onChange={(event) => changeMonitor(event.target.value)}
            >
              <option value="">All websites</option>
              {(monitors.data ?? []).map((monitor) => (
                <option key={monitor.id} value={monitor.id}>{monitor.name}</option>
              ))}
            </SelectField>
          </div>
        </div>

        <ResourceView
          state={incidents}
          skeleton={
            <div className="flex flex-col gap-3">
              <Skeleton className="h-[140px] w-full" />
              <Skeleton className="h-[140px] w-full" />
            </div>
          }
          errorTitle="Could not load the incidents."
        >
          {renderList}
        </ResourceView>
      </div>

      {incidentId !== null ? (
        <IncidentDrawer key={incidentId} incidentId={incidentId} monitorUrlFor={urlFor} onClose={() => setIncidentId(null)} />
      ) : null}
    </div>
  );
}
