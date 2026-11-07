export type MonitorStatus = "unknown" | "up" | "degraded" | "down";

export interface Monitor {
  id: number;
  name: string;
  url: string;
  routes: string[];
  api_endpoints: string[];
  alert_email: string;
  interval_minutes: number;
  enabled: boolean;
  status: MonitorStatus;
  last_checked_at: string | null;
  created_at: string;
}

export interface MonitorCreate {
  name: string;
  url: string;
  routes: string[];
  api_endpoints: string[];
  alert_email: string;
  interval_minutes: number;
  enabled: boolean;
}

export type MonitorUpdate = Partial<MonitorCreate>;

export interface CheckRead {
  id: number;
  checked_at: string;
  ok: boolean;
  status_code: number | null;
  response_time_ms: number | null;
  issues: string[];
}

export interface CheckHistory {
  monitor_id: number;
  hours: number;
  total_checks: number;
  uptime_percent: number | null;
  avg_response_ms: number | null;
  checks: CheckRead[];
}

export type Severity = "low" | "medium" | "high" | "critical";

export interface Incident {
  id: number;
  monitor_id: number;
  monitor_name: string;
  started_at: string;
  resolved_at: string | null;
  duration_minutes: number;
  status: "open" | "resolved";
  severity: Severity;
  summary: string;
  probable_cause: string;
  affected: string[];
  suggestions: string[];
  analyzed: boolean;
  alert_sent: boolean;
}

export interface AgentStatus {
  scheduler_running: boolean;
  agent_enabled: boolean;
  email_configured: boolean;
  agent_runs_24h: number;
  agent_runs_limit: number;
  monitors_total: number;
  monitors_up: number;
  monitors_degraded: number;
  monitors_down: number;
  monitors_unknown: number;
  monitors_paused: number;
  open_incidents: number;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}
