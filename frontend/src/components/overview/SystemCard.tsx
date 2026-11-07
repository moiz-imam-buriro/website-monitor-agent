import { Card, CardHeader, Skeleton } from "@/components/ui/Layout";
import { ResourceView } from "@/components/ui/ErrorNotice";
import type { PollResult } from "@/hooks/usePolling";
import type { AgentStatus } from "@/types";

interface SystemCardProps {
  agent: PollResult<AgentStatus>;
}

function Row({ label, value, ok }: { label: string; value: string; ok: boolean | null }) {
  return (
    <div className="flex min-w-0 items-center justify-between gap-3 border-b border-line py-3 last:border-b-0">
      <span className="min-w-0 text-sm text-subtle">{label}</span>
      <span className="flex min-w-0 items-center gap-2 text-right text-sm font-medium text-ink">
        {ok !== null ? (
          <span aria-hidden="true" className={ok ? "size-1.5 shrink-0 rounded-full bg-up" : "size-1.5 shrink-0 rounded-full bg-down"} />
        ) : null}
        <span className="truncate">{value}</span>
      </span>
    </div>
  );
}

export function SystemCard({ agent }: SystemCardProps) {
  return (
    <Card>
      <CardHeader title="System" />
      <ResourceView
        state={agent}
        skeleton={<Skeleton className="h-[200px] w-full" />}
        errorTitle="Could not load the system status."
      >
        {(status) => (
          <div className="flex flex-col">
            <Row label="Automatic checks" value={status.scheduler_running ? "Running" : "Stopped"} ok={status.scheduler_running} />
            <Row label="AI agent" value={status.agent_enabled ? "On" : "Off"} ok={status.agent_enabled} />
            <Row label="Email alerts" value={status.email_configured ? "Configured" : "Not configured"} ok={status.email_configured} />
            <Row
              label="AI runs in last 24 h"
              value={`${status.agent_runs_24h} of ${status.agent_runs_limit}`}
              ok={null}
            />
          </div>
        )}
      </ResourceView>
    </Card>
  );
}
