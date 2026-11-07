import { NavLink, useNavigate } from "react-router-dom";
import { Activity, Globe, LayoutDashboard, LogOut, Moon, Sun, TriangleAlert } from "lucide-react";
import { useTheme } from "@/hooks/useTheme";
import { clearSession } from "@/lib/session";
import { cn } from "@/lib/cn";
import { Switch } from "@/components/ui/Switch";

const NAV_ITEMS = [
  { to: "/", label: "Overview", icon: LayoutDashboard, end: true },
  { to: "/websites", label: "Websites", icon: Globe, end: false },
  { to: "/incidents", label: "Incidents", icon: TriangleAlert, end: false },
];

interface SidebarProps {
  onNavigate?: () => void;
}

export function Sidebar({ onNavigate }: SidebarProps) {
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const isDark = theme === "dark";

  const signOut = () => {
    clearSession();
    onNavigate?.();
    navigate("/login", { replace: true });
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-6 overflow-y-auto p-4">
      <div className="flex items-center gap-3 px-2 pt-2">
        <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-accent text-accent-ink">
          <Activity size={18} aria-hidden="true" />
        </span>
        <span className="text-sm font-semibold leading-5 text-ink">Website Monitor Agent</span>
      </div>

      <nav aria-label="Main" className="flex flex-col gap-1">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            onClick={onNavigate}
            className={({ isActive }) =>
              cn(
                "flex h-10 items-center gap-3 rounded-lg px-3 text-sm transition-colors duration-150",
                isActive ? "bg-hover font-medium text-ink" : "text-subtle hover:bg-hover hover:text-ink",
              )
            }
          >
            <item.icon size={18} aria-hidden="true" />
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="mt-auto flex flex-col gap-2 border-t border-line pt-4">
        <div className="flex h-10 items-center justify-between gap-3 px-2">
          <span className="flex items-center gap-3 text-sm text-subtle">
            {isDark ? <Moon size={18} aria-hidden="true" /> : <Sun size={18} aria-hidden="true" />}
            {isDark ? "Dark theme" : "Light theme"}
          </span>
          <Switch checked={isDark} onChange={() => toggleTheme()} label="Dark theme" />
        </div>
        <button
          type="button"
          onClick={signOut}
          className="flex h-10 items-center gap-3 rounded-lg px-3 text-sm text-subtle transition-colors duration-150 hover:bg-hover hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
        >
          <LogOut size={18} aria-hidden="true" />
          Sign out
        </button>
        <p className="px-2 pt-3 text-xs text-muted">Moiz Imam | AI Engineer</p>
      </div>
    </div>
  );
}
