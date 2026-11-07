import { useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { Activity, Eye, EyeOff, LoaderCircle } from "lucide-react";
import { describeError, getHealth, login, type HealthResponse } from "@/api";
import { Button } from "@/components/ui/Button";
import { ErrorNotice } from "@/components/ui/ErrorNotice";
import { TextField } from "@/components/ui/Fields";
import { usePolling, type PollResult } from "@/hooks/usePolling";
import { getSession, saveSession } from "@/lib/session";

const HEALTH_INTERVAL_MS = 10_000;

function ServerLine({ state }: { state: PollResult<HealthResponse> }) {
  if (state.error) {
    return (
      <p className="flex items-start gap-2 text-xs text-down">
        <span aria-hidden="true" className="mt-1 size-1.5 shrink-0 rounded-full bg-down" />
        <span className="min-w-0 break-words">{describeError(state.error).message}</span>
      </p>
    );
  }
  if (state.data) {
    return (
      <p className="flex items-center gap-2 text-xs text-subtle">
        <span aria-hidden="true" className="size-1.5 rounded-full bg-up" />
        Server is online
      </p>
    );
  }
  return <p className="text-xs text-muted">Checking the server...</p>;
}

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from ?? "/";
  const health = usePolling("login-health", (signal) => getHealth(signal), HEALTH_INTERVAL_MS);

  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);

  if (getSession()) return <Navigate to={from} replace />;

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!password) {
      setPasswordError("Enter the dashboard password.");
      return;
    }
    setPasswordError(null);
    setError(null);
    setSubmitting(true);
    try {
      const result = await login(password);
      if (typeof result.access_token !== "string" || typeof result.expires_in !== "number") {
        throw new Error("The server sent an answer the dashboard could not read.");
      }
      saveSession(result.access_token, result.expires_in);
      navigate(from, { replace: true });
    } catch (caught) {
      setError(caught);
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-dvh items-center justify-center bg-page px-4 py-10">
      <div className="w-full max-w-[400px] min-w-0 rounded-xl border border-line bg-card p-6 sm:p-8">
        <div className="flex items-center gap-3">
          <span className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-accent text-accent-ink">
            <Activity size={20} aria-hidden="true" />
          </span>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-ink">Website Monitor Agent</p>
            <p className="text-xs text-subtle">Sign in to continue</p>
          </div>
        </div>

        <form onSubmit={onSubmit} noValidate className="mt-8 flex flex-col gap-5">
          <div className="flex flex-col gap-2">
            <TextField
              id="login-password"
              label="Password"
              type={showPassword ? "text" : "password"}
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              error={passwordError}
              disabled={submitting}
              autoFocus
            />
            <button
              type="button"
              onClick={() => setShowPassword((current) => !current)}
              className="inline-flex w-fit items-center gap-1.5 text-xs font-medium text-accent hover:underline"
            >
              {showPassword ? <EyeOff size={14} aria-hidden="true" /> : <Eye size={14} aria-hidden="true" />}
              {showPassword ? "Hide password" : "Show password"}
            </button>
          </div>

          {error ? <ErrorNotice error={error} /> : null}

          <Button type="submit" variant="primary" loading={submitting} className="w-full">
            {submitting ? (
              <span className="inline-flex items-center gap-2">
                <LoaderCircle size={16} aria-hidden="true" className="animate-spin" />
                Signing in
              </span>
            ) : (
              "Sign in"
            )}
          </Button>
        </form>

        <div className="mt-6 border-t border-line pt-4">
          <ServerLine state={health} />
        </div>
      </div>
    </div>
  );
}
