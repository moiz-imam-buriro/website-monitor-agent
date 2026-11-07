import { useState } from "react";
import { Outlet } from "react-router-dom";
import { Activity, Menu } from "lucide-react";
import { IconButton } from "@/components/ui/Button";
import { Drawer } from "@/components/ui/Overlays";
import { OfflineBanner } from "@/components/ui/OfflineBanner";
import { Sidebar } from "@/components/layout/Sidebar";

export function AppShell() {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className="min-h-dvh bg-page text-ink">
      <aside className="fixed inset-y-0 left-0 z-20 hidden w-[248px] flex-col border-r border-line bg-card lg:flex">
        <Sidebar />
      </aside>

      <div className="flex min-h-dvh min-w-0 flex-col lg:pl-[248px]">
        <header className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-line bg-card px-4 lg:hidden">
          <IconButton label="Open menu" onClick={() => setMenuOpen(true)}>
            <Menu size={20} aria-hidden="true" />
          </IconButton>
          <span className="flex min-w-0 items-center gap-2">
            <span className="flex size-7 shrink-0 items-center justify-center rounded-md bg-accent text-accent-ink">
              <Activity size={15} aria-hidden="true" />
            </span>
            <span className="truncate text-sm font-semibold text-ink">Website Monitor Agent</span>
          </span>
        </header>

        <OfflineBanner />

        <main className="mx-auto w-full max-w-[1280px] min-w-0 flex-1 px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
          <Outlet />
        </main>
      </div>

      {menuOpen ? (
        <Drawer side="left" title={<span className="text-base font-medium text-ink">Menu</span>} onClose={() => setMenuOpen(false)}>
          <Sidebar onNavigate={() => setMenuOpen(false)} />
        </Drawer>
      ) : null}
    </div>
  );
}
