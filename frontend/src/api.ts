import type {
  AgentStatus,
  CheckHistory,
  Incident,
  LoginResponse,
  Monitor,
  MonitorCreate,
  MonitorUpdate,
} from "@/types";
import { clearSession, getSession } from "@/lib/session";

const raw = (import.meta.env.VITE_API_URL ?? "").trim();
export const API_BASE =
  raw === "same-origin" ? "" : raw !== "" ? raw.replace(/\/+$/, "") : import.meta.env.DEV ? "http://127.0.0.1:8000" : "";

export const SESSION_EXPIRED_EVENT = "wm:session-expired";

const REQUEST_TIMEOUT_MS = 20_000;
const MAX_RESPONSE_TEXT = 2000;
const PUBLIC_PATHS: ReadonlySet<string> = new Set(["/health", "/auth/login"]);

const OFFLINE_MESSAGE = "You're offline. Check your Wi-Fi or mobile data.";
const TIMEOUT_MESSAGE = "The server took too long to answer (over 20 seconds).";
const BAD_ANSWER_MESSAGE = "The server sent an answer the dashboard could not read.";
const SESSION_EXPIRED_MESSAGE = "Your session expired. Sign in again.";
const ALREADY_RUNNING_MESSAGE = "A check is already running.";

export type ApiErrorKind = "offline" | "unreachable" | "timeout" | "http" | "bad_answer";

export interface TechnicalInfo {
  method: string;
  url: string;
  status: number | null;
  networkError: string | null;
  responseText: string | null;
}

export interface FieldIssue {
  field: string | null;
  message: string;
}

interface ApiErrorInit {
  kind: ApiErrorKind;
  message: string;
  technical: TechnicalInfo;
  status?: number | null;
  issues?: FieldIssue[];
}

export class ApiError extends Error {
  readonly kind: ApiErrorKind;
  readonly status: number | null;
  readonly technical: TechnicalInfo;
  readonly issues: FieldIssue[];

  constructor(init: ApiErrorInit) {
    super(init.message);
    this.name = "ApiError";
    this.kind = init.kind;
    this.status = init.status ?? null;
    this.technical = init.technical;
    this.issues = init.issues ?? [];
  }
}

export interface HealthResponse {
  status: string;
  app: string;
}

export interface CheckNowResponse {
  message: string;
}

export interface TestEmailResponse {
  sent: boolean;
  to: string;
}

export interface IncidentFilters {
  monitor_id?: number;
  status?: "open" | "resolved";
  limit?: number;
  offset?: number;
}

export function isAbortError(error: unknown): boolean {
  return typeof error === "object" && error !== null && "name" in error && error.name === "AbortError";
}

export function describeError(error: unknown): { message: string; technical: TechnicalInfo | null } {
  if (error instanceof ApiError) return { message: error.message, technical: error.technical };
  const message = error instanceof Error && error.message ? error.message : "The dashboard could not finish this action.";
  return { message, technical: null };
}

function unreachableMessage(): string {
  const where = API_BASE || "this address";
  const hint = import.meta.env.DEV ? " Make sure the backend is running." : "";
  return `Can't reach the server at ${where}. The server may be stopped, or its address may be wrong.${hint}`;
}

function readErrorBody(text: string): { message: string | null; issues: FieldIssue[] } {
  let body: unknown;
  try {
    body = JSON.parse(text);
  } catch {
    return { message: null, issues: [] };
  }
  if (typeof body !== "object" || body === null || !("detail" in body)) {
    return { message: null, issues: [] };
  }
  const detail = body.detail;
  if (typeof detail === "string") {
    return { message: detail.trim() || null, issues: [] };
  }
  if (Array.isArray(detail)) {
    const issues: FieldIssue[] = [];
    for (const item of detail) {
      if (typeof item !== "object" || item === null || !("msg" in item) || typeof item.msg !== "string") continue;
      const loc: unknown[] = "loc" in item && Array.isArray(item.loc) ? item.loc : [];
      const field = loc.filter((part): part is string => typeof part === "string" && part !== "body").pop() ?? null;
      issues.push({ field, message: item.msg });
    }
    return { message: issues.map((issue) => issue.message).join(" ") || null, issues };
  }
  return { message: null, issues: [] };
}

function httpError(status: number, text: string, technical: TechnicalInfo): ApiError {
  const { message, issues } = readErrorBody(text);
  let resolved = message ?? `The server returned an error (HTTP ${status}).`;
  if (status === 409) resolved = ALREADY_RUNNING_MESSAGE;
  return new ApiError({ kind: "http", status, message: resolved, technical, issues });
}

function errorName(error: unknown): string {
  return error instanceof Error ? error.name : "UnknownError";
}

interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  signal?: AbortSignal;
  expect?: "object" | "array" | "none";
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const method = options.method ?? "GET";
  const url = `${API_BASE}${path}`;
  const isPublic = PUBLIC_PATHS.has(path);
  const technical: TechnicalInfo = {
    method,
    url: new URL(url, window.location.href).href,
    status: null,
    networkError: null,
    responseText: null,
  };

  if (!navigator.onLine) {
    throw new ApiError({
      kind: "offline",
      message: OFFLINE_MESSAGE,
      technical: { ...technical, networkError: "Browser reports no connection" },
    });
  }

  const headers: Record<string, string> = { Accept: "application/json" };
  if (options.body !== undefined) headers["Content-Type"] = "application/json";
  if (!isPublic) {
    const session = getSession();
    if (!session) {
      window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT));
      throw new ApiError({ kind: "http", status: 401, message: SESSION_EXPIRED_MESSAGE, technical });
    }
    headers.Authorization = `Bearer ${session.token}`;
  }

  const controller = new AbortController();
  let timedOut = false;
  const timer = window.setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, REQUEST_TIMEOUT_MS);
  const cancel = () => controller.abort();
  options.signal?.addEventListener("abort", cancel);
  if (options.signal?.aborted) controller.abort();

  let response: Response;
  let text: string;
  try {
    response = await fetch(url, {
      method,
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      signal: controller.signal,
    });
    text = await response.text();
  } catch (error) {
    if (isAbortError(error) && !timedOut) throw error;
    if (timedOut) {
      throw new ApiError({ kind: "timeout", message: TIMEOUT_MESSAGE, technical: { ...technical, networkError: "AbortError" } });
    }
    if (!navigator.onLine) {
      throw new ApiError({
        kind: "offline",
        message: OFFLINE_MESSAGE,
        technical: { ...technical, networkError: errorName(error) },
      });
    }
    throw new ApiError({
      kind: "unreachable",
      message: unreachableMessage(),
      technical: { ...technical, networkError: errorName(error) },
    });
  } finally {
    window.clearTimeout(timer);
    options.signal?.removeEventListener("abort", cancel);
  }

  technical.status = response.status;
  technical.responseText = text.slice(0, MAX_RESPONSE_TEXT) || null;

  if (!response.ok) {
    if (response.status === 401 && !isPublic) {
      clearSession();
      window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT));
      throw new ApiError({ kind: "http", status: 401, message: SESSION_EXPIRED_MESSAGE, technical });
    }
    throw httpError(response.status, text, technical);
  }

  const expect = options.expect ?? "object";
  if (response.status === 204 || expect === "none") return undefined as T;

  let data: unknown;
  try {
    data = JSON.parse(text);
  } catch {
    throw new ApiError({ kind: "bad_answer", message: BAD_ANSWER_MESSAGE, technical });
  }
  const valid =
    expect === "array"
      ? Array.isArray(data)
      : typeof data === "object" && data !== null && !Array.isArray(data);
  if (!valid) throw new ApiError({ kind: "bad_answer", message: BAD_ANSWER_MESSAGE, technical });
  return data as T;
}

function withQuery(path: string, params: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined) search.set(key, String(value));
  }
  const query = search.toString();
  return query ? `${path}?${query}` : path;
}

export function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  return request<HealthResponse>("/health", { signal });
}

export function login(password: string): Promise<LoginResponse> {
  return request<LoginResponse>("/auth/login", { method: "POST", body: { password } });
}

export function getAgentStatus(signal?: AbortSignal): Promise<AgentStatus> {
  return request<AgentStatus>("/agent/status", { signal });
}

export function listMonitors(signal?: AbortSignal): Promise<Monitor[]> {
  return request<Monitor[]>("/monitors", { signal, expect: "array" });
}

export function getMonitor(id: number, signal?: AbortSignal): Promise<Monitor> {
  return request<Monitor>(`/monitors/${id}`, { signal });
}

export function createMonitor(body: MonitorCreate): Promise<Monitor> {
  return request<Monitor>("/monitors", { method: "POST", body });
}

export function updateMonitor(id: number, body: MonitorUpdate): Promise<Monitor> {
  return request<Monitor>(`/monitors/${id}`, { method: "PATCH", body });
}

export function deleteMonitor(id: number): Promise<void> {
  return request<void>(`/monitors/${id}`, { method: "DELETE", expect: "none" });
}

export function getCheckHistory(id: number, hours: number, limit: number, signal?: AbortSignal): Promise<CheckHistory> {
  return request<CheckHistory>(withQuery(`/monitors/${id}/checks`, { hours, limit }), { signal });
}

export function checkMonitorNow(id: number): Promise<CheckNowResponse> {
  return request<CheckNowResponse>(`/monitors/${id}/check-now`, { method: "POST" });
}

export function sendTestEmail(id: number): Promise<TestEmailResponse> {
  return request<TestEmailResponse>(`/monitors/${id}/test-email`, { method: "POST" });
}

export function listIncidents(filters: IncidentFilters, signal?: AbortSignal): Promise<Incident[]> {
  const path = withQuery("/incidents", {
    monitor_id: filters.monitor_id,
    status: filters.status,
    limit: filters.limit,
    offset: filters.offset,
  });
  return request<Incident[]>(path, { signal, expect: "array" });
}

export function getIncident(id: number, signal?: AbortSignal): Promise<Incident> {
  return request<Incident>(`/incidents/${id}`, { signal });
}
