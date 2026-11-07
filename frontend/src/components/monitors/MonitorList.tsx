import { Eye, Ellipsis, LoaderCircle, Mail, Pencil, RefreshCw, Trash2 } from "lucide-react";
import { IconButton, Button } from "@/components/ui/Button";
import { SiteIcon } from "@/components/ui/SiteIcon";
import { StatusBadge } from "@/components/ui/Badge";
import { BottomSheet } from "@/components/ui/Overlays";
import { displayStatus, formatInterval, formatRelative, hostnameOf } from "@/lib/format";
import { useState } from "react";
import type { Monitor } from "@/types";

export interface MonitorActions {
  onOpen: (monitor: Monitor) => void;
  onEdit: (monitor: Monitor) => void;
  onCheck: (monitor: Monitor) => void;
  onTestEmail: (monitor: Monitor) => void;
  onDelete: (monitor: Monitor) => void;
}

interface MonitorListProps {
  monitors: Monitor[];
  busyIds: ReadonlySet<number>;
  actions: MonitorActions;
}

function NameButton({ monitor, onOpen }: { monitor: Monitor; onOpen: (monitor: Monitor) => void }) {
  return (
    <button
      type="button"
      onClick={() => onOpen(monitor)}
      className="flex min-w-0 items-center gap-3 rounded-lg text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
    >
      <SiteIcon url={monitor.url} name={monitor.name} />
      <span className="min-w-0">
        <span className="block truncate text-sm font-medium text-ink hover:underline">{monitor.name}</span>
        <span className="block truncate text-xs text-subtle">{hostnameOf(monitor.url) || monitor.url}</span>
      </span>
    </button>
  );
}

function DesktopTable({ monitors, busyIds, actions }: MonitorListProps) {
  return (
    <div className="hidden min-w-0 overflow-hidden rounded-xl border border-line bg-card lg:block">
      <table className="w-full table-fixed text-left text-sm">
        <colgroup>
          <col className="w-[40%]" />
          <col className="w-[16%]" />
          <col className="w-[18%]" />
          <col className="w-[12%]" />
          <col className="w-[14%]" />
        </colgroup>
        <thead className="border-b border-line bg-page text-xs text-subtle">
          <tr>
            <th scope="col" className="px-4 py-3 font-medium">Website</th>
            <th scope="col" className="px-4 py-3 font-medium">Status</th>
            <th scope="col" className="px-4 py-3 font-medium">Last checked</th>
            <th scope="col" className="px-4 py-3 font-medium">Interval</th>
            <th scope="col" className="px-4 py-3 text-right font-medium"><span className="sr-only">Actions</span></th>
          </tr>
        </thead>
        <tbody>
          {monitors.map((monitor) => {
            const busy = busyIds.has(monitor.id);
            return (
              <tr key={monitor.id} className="border-b border-line last:border-b-0 hover:bg-hover">
                <td className="px-4 py-3"><NameButton monitor={monitor} onOpen={actions.onOpen} /></td>
                <td className="px-4 py-3"><StatusBadge status={displayStatus(monitor)} /></td>
                <td className="truncate px-4 py-3 text-subtle">{formatRelative(monitor.last_checked_at)}</td>
                <td className="truncate px-4 py-3 text-subtle">{formatInterval(monitor.interval_minutes)}</td>
                <td className="px-4 py-3">
                  <div className="flex items-center justify-end gap-1">
                    <IconButton label={`Check ${monitor.name} now`} onClick={() => actions.onCheck(monitor)} disabled={busy}>
                      {busy ? <LoaderCircle size={16} aria-hidden="true" className="animate-spin" /> : <RefreshCw size={16} aria-hidden="true" />}
                    </IconButton>
                    <IconButton label={`Edit ${monitor.name}`} onClick={() => actions.onEdit(monitor)}>
                      <Pencil size={16} aria-hidden="true" />
                    </IconButton>
                    <IconButton label={`Delete ${monitor.name}`} onClick={() => actions.onDelete(monitor)} className="hover:text-down">
                      <Trash2 size={16} aria-hidden="true" />
                    </IconButton>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function MobileCard({ monitor, busy, onMore }: { monitor: Monitor; busy: boolean; onMore: (monitor: Monitor) => void }) {
  return (
    <li className="flex min-w-0 items-start gap-3 rounded-xl border border-line bg-card p-4">
      <div className="min-w-0 flex-1">
        <NameButton monitor={monitor} onOpen={() => onMore(monitor)} />
        <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-2 text-xs text-subtle">
          <StatusBadge status={displayStatus(monitor)} />
          <span>{formatRelative(monitor.last_checked_at)}</span>
          <span aria-hidden="true">|</span>
          <span>{formatInterval(monitor.interval_minutes)}</span>
          {busy ? <LoaderCircle size={14} aria-label="Checking" className="animate-spin text-accent" /> : null}
        </div>
      </div>
      <IconButton label={`More actions for ${monitor.name}`} onClick={() => onMore(monitor)}>
        <Ellipsis size={18} aria-hidden="true" />
      </IconButton>
    </li>
  );
}

function MobileList({ monitors, busyIds, actions }: MonitorListProps) {
  const [sheetMonitor, setSheetMonitor] = useState<Monitor | null>(null);
  const run = (action: (monitor: Monitor) => void, monitor: Monitor) => {
    setSheetMonitor(null);
    action(monitor);
  };

  return (
    <>
      <ul className="flex min-w-0 flex-col gap-3 lg:hidden">
        {monitors.map((monitor) => (
          <MobileCard key={monitor.id} monitor={monitor} busy={busyIds.has(monitor.id)} onMore={setSheetMonitor} />
        ))}
      </ul>
      {sheetMonitor ? (
        <BottomSheet title={sheetMonitor.name} onClose={() => setSheetMonitor(null)}>
          <div className="flex flex-col gap-1">
            <Button variant="ghost" icon={<Eye size={16} aria-hidden="true" />} className="h-11 justify-start" onClick={() => run(actions.onOpen, sheetMonitor)}>View details</Button>
            <Button variant="ghost" icon={<RefreshCw size={16} aria-hidden="true" />} className="h-11 justify-start" onClick={() => run(actions.onCheck, sheetMonitor)}>Check now</Button>
            <Button variant="ghost" icon={<Mail size={16} aria-hidden="true" />} className="h-11 justify-start" onClick={() => run(actions.onTestEmail, sheetMonitor)}>Send test email</Button>
            <Button variant="ghost" icon={<Pencil size={16} aria-hidden="true" />} className="h-11 justify-start" onClick={() => run(actions.onEdit, sheetMonitor)}>Edit</Button>
            <Button variant="ghost" icon={<Trash2 size={16} aria-hidden="true" />} className="h-11 justify-start text-down" onClick={() => run(actions.onDelete, sheetMonitor)}>Delete</Button>
          </div>
        </BottomSheet>
      ) : null}
    </>
  );
}

export function MonitorList(props: MonitorListProps) {
  return (
    <>
      <DesktopTable {...props} />
      <MobileList {...props} />
    </>
  );
}
