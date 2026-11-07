import type { Monitor, MonitorStatus, Severity } from "@/types";

export type DisplayStatus = MonitorStatus | "paused";

export const STATUS_LABEL: Record<DisplayStatus, string> = {
  up: "Up",
  degraded: "Degraded",
  down: "Down",
  unknown: "Not checked yet",
  paused: "Paused",
};

export const SEVERITY_LABEL: Record<Severity, string> = {
  low: "Low",
  medium: "Medium",
  high: "High",
  critical: "Critical",
};

export function displayStatus(monitor: Pick<Monitor, "enabled" | "status">): DisplayStatus {
  return monitor.enabled ? monitor.status : "paused";
}

export function formatExact(iso: string): string {
  const time = Date.parse(iso);
  if (Number.isNaN(time)) return "Unknown time";
  return new Date(time).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

export function formatRelative(iso: string | null, now: number = Date.now()): string {
  if (!iso) return "Never";
  const time = Date.parse(iso);
  if (Number.isNaN(time)) return "Unknown time";
  const seconds = Math.round((now - time) / 1000);
  if (seconds < 45) return "Just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days} ${days === 1 ? "day" : "days"} ago`;
  return new Date(time).toLocaleDateString(undefined, { dateStyle: "medium" });
}

export function formatDuration(totalMinutes: number): string {
  const minutes = Math.max(0, Math.floor(totalMinutes));
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return rest === 0 ? `${hours} h` : `${hours} h ${rest} min`;
}

export function formatMs(ms: number | null): string {
  if (ms === null) return "n/a";
  return `${Math.round(ms).toLocaleString()} ms`;
}

export function formatPercent(percent: number | null): string {
  if (percent === null) return "n/a";
  return `${Number(percent.toFixed(1))}%`;
}

export function formatInterval(minutes: number): string {
  return `Every ${minutes} min`;
}

export function hostnameOf(url: string): string {
  try {
    return new URL(url).hostname;
  } catch {
    return "";
  }
}
