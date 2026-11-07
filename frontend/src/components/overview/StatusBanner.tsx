import { TriangleAlert } from "lucide-react";
import type { AgentStatus } from "@/types";

interface StatusBannerProps {
  status: AgentStatus;
}

export function StatusBanner({ status }: StatusBannerProps) {
  const issues: string[] = [];
  if (!status.scheduler_running) issues.push("Automatic checks are stopped on the server, so websites are not being monitored.");
  if (!status.agent_enabled) issues.push("The AI incident agent is turned off on the server, so incidents are not explained.");
  if (!status.email_configured) issues.push("Email alerts are not configured on the server, so you will not receive incident emails.");
  if (issues.length === 0) return null;

  return (
    <div role="status" className="flex min-w-0 gap-3 rounded-xl border border-line bg-degraded-tint p-4">
      <TriangleAlert size={18} aria-hidden="true" className="mt-0.5 shrink-0 text-degraded" />
      <ul className="flex min-w-0 flex-col gap-1.5 text-sm text-degraded">
        {issues.map((issue) => (
          <li key={issue} className="break-words">{issue}</li>
        ))}
      </ul>
    </div>
  );
}
