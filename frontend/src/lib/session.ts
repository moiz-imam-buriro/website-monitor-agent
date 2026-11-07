const SESSION_KEY = "wm_session";

export interface Session {
  token: string;
  expiresAt: number;
}

function parseSession(raw: string): Session | null {
  try {
    const value = JSON.parse(raw) as Partial<Session>;
    if (typeof value.token === "string" && typeof value.expiresAt === "number") {
      return { token: value.token, expiresAt: value.expiresAt };
    }
    return null;
  } catch {
    return null;
  }
}

export function getSession(): Session | null {
  const raw = window.localStorage.getItem(SESSION_KEY);
  if (raw === null) return null;
  const session = parseSession(raw);
  if (session && session.expiresAt > Date.now()) return session;
  clearSession();
  return null;
}

export function saveSession(token: string, expiresInSeconds: number): void {
  const session: Session = { token, expiresAt: Date.now() + expiresInSeconds * 1000 };
  window.localStorage.setItem(SESSION_KEY, JSON.stringify(session));
}

export function clearSession(): void {
  window.localStorage.removeItem(SESSION_KEY);
}
