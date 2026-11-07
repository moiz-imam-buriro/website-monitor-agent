import { useState, type FormEvent } from "react";
import { ApiError, createMonitor, isAbortError, updateMonitor, type FieldIssue } from "@/api";
import { ErrorNotice } from "@/components/ui/ErrorNotice";
import { SelectField, TextField } from "@/components/ui/Fields";
import { TagInput } from "@/components/ui/TagInput";
import { Switch } from "@/components/ui/Switch";
import { formatInterval } from "@/lib/format";
import type { Monitor, MonitorCreate } from "@/types";

export const MONITOR_FORM_ID = "monitor-form";
const INTERVALS = [1, 5, 10, 15, 30, 60];
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

type FormKey = "name" | "url" | "routes" | "api_endpoints" | "alert_email" | "interval_minutes";
type FormErrors = Partial<Record<FormKey, string>>;

interface FormState {
  name: string;
  url: string;
  routes: string[];
  api_endpoints: string[];
  alert_email: string;
  interval_minutes: number;
  enabled: boolean;
}

function initialState(monitor: Monitor | null): FormState {
  if (!monitor) {
    return { name: "", url: "", routes: [], api_endpoints: [], alert_email: "", interval_minutes: 5, enabled: true };
  }
  return {
    name: monitor.name,
    url: monitor.url,
    routes: monitor.routes,
    api_endpoints: monitor.api_endpoints,
    alert_email: monitor.alert_email,
    interval_minutes: monitor.interval_minutes,
    enabled: monitor.enabled,
  };
}

function validate(form: FormState): FormErrors {
  const errors: FormErrors = {};
  if (!form.name.trim()) errors.name = "Enter a name for this website.";
  try {
    const parsed = new URL(form.url.trim());
    if (parsed.protocol !== "http:" && parsed.protocol !== "https:") errors.url = "The address must start with http:// or https://.";
  } catch {
    errors.url = "Enter a full address, for example https://example.com.";
  }
  if (!EMAIL_PATTERN.test(form.alert_email.trim())) errors.alert_email = "Enter a valid email address for alerts.";
  return errors;
}

function toPayload(form: FormState): MonitorCreate {
  return {
    name: form.name.trim(),
    url: form.url.trim(),
    routes: form.routes,
    api_endpoints: form.api_endpoints,
    alert_email: form.alert_email.trim(),
    interval_minutes: form.interval_minutes,
    enabled: form.enabled,
  };
}

const FORM_KEYS: readonly string[] = ["name", "url", "routes", "api_endpoints", "alert_email", "interval_minutes"];

function mapIssues(issues: FieldIssue[]): FormErrors {
  const fieldErrors: FormErrors = {};
  for (const issue of issues) {
    if (issue.field && FORM_KEYS.includes(issue.field)) fieldErrors[issue.field as FormKey] = issue.message;
  }
  return fieldErrors;
}

interface MonitorFormProps {
  monitor: Monitor | null;
  onSaved: (monitor: Monitor) => void;
  onSavingChange: (saving: boolean) => void;
}

export function MonitorForm({ monitor, onSaved, onSavingChange }: MonitorFormProps) {
  const [form, setForm] = useState<FormState>(() => initialState(monitor));
  const [errors, setErrors] = useState<FormErrors>({});
  const [serverError, setServerError] = useState<unknown>(null);
  const [saving, setSaving] = useState(false);

  const update = <K extends keyof FormState>(key: K, value: FormState[K]) => {
    setForm((current) => ({ ...current, [key]: value }));
  };

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const found = validate(form);
    setErrors(found);
    setServerError(null);
    if (Object.keys(found).length > 0) return;

    setSaving(true);
    onSavingChange(true);
    try {
      const payload = toPayload(form);
      const saved = monitor ? await updateMonitor(monitor.id, payload) : await createMonitor(payload);
      onSaved(saved);
    } catch (caught) {
      if (isAbortError(caught)) return;
      if (caught instanceof ApiError) setErrors(mapIssues(caught.issues));
      setServerError(caught);
    } finally {
      setSaving(false);
      onSavingChange(false);
    }
  }

  return (
    <form id={MONITOR_FORM_ID} onSubmit={onSubmit} noValidate className="flex flex-col gap-5">
      <TextField id="monitor-name" label="Name" value={form.name} error={errors.name} disabled={saving}
        onChange={(event) => update("name", event.target.value)} placeholder="Company homepage" maxLength={80} />
      <TextField id="monitor-url" label="Address" inputMode="url" value={form.url} error={errors.url} disabled={saving}
        onChange={(event) => update("url", event.target.value)} placeholder="https://example.com" />
      <TagInput id="monitor-routes" label="Pages to check" values={form.routes} onChange={(v) => update("routes", v)}
        placeholder="/pricing" hint="Type a path and press Enter. Paths start with /." error={errors.routes} />
      <TagInput id="monitor-endpoints" label="API endpoints to check" values={form.api_endpoints}
        onChange={(v) => update("api_endpoints", v)} placeholder="/api/health" hint="Optional. Press Enter after each one."
        error={errors.api_endpoints} />
      <TextField id="monitor-email" label="Alert email" type="email" value={form.alert_email} error={errors.alert_email}
        disabled={saving} onChange={(event) => update("alert_email", event.target.value)} placeholder="you@example.com" />
      <SelectField id="monitor-interval" label="Check interval" value={form.interval_minutes} error={errors.interval_minutes}
        disabled={saving} onChange={(event) => update("interval_minutes", Number(event.target.value))}>
        {INTERVALS.map((minutes) => (
          <option key={minutes} value={minutes}>{formatInterval(minutes)}</option>
        ))}
      </SelectField>
      <div className="flex items-center justify-between gap-4 rounded-lg border border-line p-4">
        <div className="min-w-0">
          <p className="text-sm font-medium text-ink">Monitoring enabled</p>
          <p className="text-xs text-subtle">Paused websites are not checked.</p>
        </div>
        <Switch checked={form.enabled} onChange={(v) => update("enabled", v)} label="Monitoring enabled" disabled={saving} />
      </div>
      {serverError ? <ErrorNotice error={serverError} /> : null}
    </form>
  );
}
