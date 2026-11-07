import { useState } from "react";
import { Link } from "react-router-dom";
import { MonitorHistory } from "@/components/monitors/MonitorHistory";
import { Card, CardHeader, EmptyState, Skeleton } from "@/components/ui/Layout";
import { ResourceView } from "@/components/ui/ErrorNotice";
import { SelectField } from "@/components/ui/Fields";
import type { PollResult } from "@/hooks/usePolling";
import type { Monitor } from "@/types";

interface ResponseSectionProps {
  monitors: PollResult<Monitor[]>;
}

function ResponseCard({ monitors }: { monitors: Monitor[] }) {
  const [selectedId, setSelectedId] = useState<number | null>(null);

  if (monitors.length === 0) {
    return (
      <Card>
        <CardHeader title="Response time" />
        <EmptyState
          title="No websites yet"
          description="Add a website to start seeing its response times here."
          action={<Link to="/websites" className="text-sm font-medium text-accent hover:underline">Go to websites</Link>}
        />
      </Card>
    );
  }

  const active = monitors.find((monitor) => monitor.id === selectedId) ?? monitors[0];

  return (
    <Card>
      <CardHeader
        title="Response time, last 24 h"
        action={
          <div className="w-full sm:w-64">
            <SelectField
              id="overview-website"
              label="Website"
              value={active.id}
              onChange={(event) => setSelectedId(Number(event.target.value))}
            >
              {monitors.map((monitor) => (
                <option key={monitor.id} value={monitor.id}>{monitor.name}</option>
              ))}
            </SelectField>
          </div>
        }
      />
      <MonitorHistory monitorId={active.id} hours={24} />
    </Card>
  );
}

export function ResponseSection({ monitors }: ResponseSectionProps) {
  return (
    <ResourceView
      state={monitors}
      skeleton={<Card><Skeleton className="h-[360px] w-full" /></Card>}
      errorTitle="Could not load your websites."
    >
      {(list) => <ResponseCard monitors={list} />}
    </ResourceView>
  );
}
