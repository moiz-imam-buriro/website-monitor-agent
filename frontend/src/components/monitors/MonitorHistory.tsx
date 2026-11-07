import { getCheckHistory } from "@/api";
import { usePolling } from "@/hooks/usePolling";
import { formatMs, formatPercent } from "@/lib/format";
import { ErrorCard } from "@/components/ui/ErrorNotice";
import { Skeleton } from "@/components/ui/Layout";
import { ResponseChart } from "@/components/monitors/ResponseChart";

const HISTORY_LIMIT = 1000;

interface MonitorHistoryProps {
  monitorId: number;
  hours: number;
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <p className="text-xs text-subtle">{label}</p>
      <p className="truncate text-lg font-medium tabular-nums text-ink">{value}</p>
    </div>
  );
}

export function MonitorHistory({ monitorId, hours }: MonitorHistoryProps) {
  const history = usePolling(`history-${monitorId}-${hours}`, (signal) =>
    getCheckHistory(monitorId, hours, HISTORY_LIMIT, signal),
  );

  if (history.data === null) {
    if (history.error) {
      return <ErrorCard title="Could not load the response times." error={history.error} onRetry={history.refresh} />;
    }
    return (
      <div className="flex flex-col gap-4">
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-[240px] w-full" />
      </div>
    );
  }

  return (
    <div className="flex min-w-0 flex-col gap-5">
      <div className="grid grid-cols-3 gap-3">
        <Stat label="Uptime" value={formatPercent(history.data.uptime_percent)} />
        <Stat label="Average" value={formatMs(history.data.avg_response_ms)} />
        <Stat label="Checks" value={history.data.total_checks.toLocaleString()} />
      </div>
      <ResponseChart checks={history.data.checks} />
    </div>
  );
}
