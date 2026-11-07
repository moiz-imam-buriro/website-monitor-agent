import { useState } from "react";
import { Plus } from "lucide-react";
import { checkMonitorNow, deleteMonitor, listMonitors, sendTestEmail, isAbortError } from "@/api";
import { Button } from "@/components/ui/Button";
import { Drawer } from "@/components/ui/Overlays";
import { EmptyState, PageHeader, Skeleton } from "@/components/ui/Layout";
import { ResourceView } from "@/components/ui/ErrorNotice";
import { MonitorList, type MonitorActions } from "@/components/monitors/MonitorList";
import { WebsiteDrawer } from "@/components/monitors/WebsiteDrawer";
import { DeleteMonitorDialog } from "@/components/monitors/DeleteMonitorDialog";
import { MONITOR_FORM_ID, MonitorForm } from "@/components/monitors/MonitorForm";
import { useIdParam } from "@/hooks/useIdParam";
import { usePolling } from "@/hooks/usePolling";
import { useToast } from "@/hooks/useToast";
import type { Monitor } from "@/types";

type FormTarget = Monitor | "new" | null;

export function WebsitesPage() {
  const toast = useToast();
  const monitors = usePolling("monitors", (signal) => listMonitors(signal));
  const [siteId, setSiteId] = useIdParam("site");
  const [formTarget, setFormTarget] = useState<FormTarget>(null);
  const [formSaving, setFormSaving] = useState(false);
  const [deleting, setDeleting] = useState<Monitor | null>(null);
  const [deletingBusy, setDeletingBusy] = useState(false);
  const [deleteError, setDeleteError] = useState<unknown>(null);
  const [busyIds, setBusyIds] = useState<ReadonlySet<number>>(() => new Set());

  const setBusy = (id: number, busy: boolean) => {
    setBusyIds((current) => {
      const next = new Set(current);
      if (busy) next.add(id);
      else next.delete(id);
      return next;
    });
  };

  const checkNow = (monitor: Monitor) => {
    setBusy(monitor.id, true);
    checkMonitorNow(monitor.id)
      .then((result) => {
        toast.success(result.message);
        monitors.refresh();
      })
      .catch((error: unknown) => {
        if (!isAbortError(error)) toast.error(error);
      })
      .finally(() => setBusy(monitor.id, false));
  };

  const testEmail = (monitor: Monitor) => {
    sendTestEmail(monitor.id)
      .then((result) => {
        if (result.sent) toast.success(`Test email sent to ${result.to}.`);
        else toast.error(new Error("The server did not send the test email. Check the email settings on the server."));
      })
      .catch((error: unknown) => toast.error(error));
  };

  const confirmDelete = async () => {
    if (!deleting) return;
    const id = deleting.id;
    setDeletingBusy(true);
    setDeleteError(null);
    try {
      await deleteMonitor(id);
      toast.success("Website deleted.");
      setDeleting(null);
      if (siteId === id) setSiteId(null);
      monitors.refresh();
    } catch (error) {
      setDeleteError(error);
    } finally {
      setDeletingBusy(false);
    }
  };

  const actions: MonitorActions = {
    onOpen: (monitor) => {
      setFormTarget(null);
      setSiteId(monitor.id);
    },
    onEdit: (monitor) => {
      setSiteId(null);
      setFormTarget(monitor);
    },
    onCheck: checkNow,
    onTestEmail: testEmail,
    onDelete: (monitor) => {
      setDeleteError(null);
      setDeleting(monitor);
    },
  };

  const formOpen = formTarget !== null;
  const drawerVisible = siteId !== null && !formOpen && deleting === null;

  return (
    <div className="flex min-w-0 flex-col gap-6">
      <PageHeader
        title="Websites"
        actions={
          <Button variant="primary" icon={<Plus size={16} aria-hidden="true" />} onClick={() => setFormTarget("new")}>
            Add website
          </Button>
        }
      />

      <ResourceView
        state={monitors}
        skeleton={
          <div className="flex flex-col gap-3">
            <Skeleton className="h-[72px] w-full" />
            <Skeleton className="h-[72px] w-full" />
            <Skeleton className="h-[72px] w-full" />
          </div>
        }
        errorTitle="Could not load your websites."
      >
        {(list) =>
          list.length === 0 ? (
            <div className="rounded-xl border border-line bg-card">
              <EmptyState
                title="No websites yet"
                description="Add a website to start checking it and getting alerts when it goes down."
                action={
                  <Button variant="primary" icon={<Plus size={16} aria-hidden="true" />} onClick={() => setFormTarget("new")}>
                    Add website
                  </Button>
                }
              />
            </div>
          ) : (
            <MonitorList monitors={list} busyIds={busyIds} actions={actions} />
          )
        }
      </ResourceView>

      {drawerVisible && siteId !== null ? (
        <WebsiteDrawer monitorId={siteId} actions={actions} busy={busyIds.has(siteId)} onClose={() => setSiteId(null)} />
      ) : null}

      {formTarget !== null ? (
        <Drawer
          title={<span className="text-base font-medium text-ink">{formTarget === "new" ? "Add website" : "Edit website"}</span>}
          onClose={() => setFormTarget(null)}
          footer={
            <div className="flex justify-end gap-2">
              <Button variant="secondary" onClick={() => setFormTarget(null)} disabled={formSaving}>Cancel</Button>
              <Button type="submit" form={MONITOR_FORM_ID} variant="primary" loading={formSaving}>
                {formTarget === "new" ? "Add website" : "Save changes"}
              </Button>
            </div>
          }
        >
          <MonitorForm
            monitor={formTarget === "new" ? null : formTarget}
            onSavingChange={setFormSaving}
            onSaved={(saved) => {
              toast.success(formTarget === "new" ? "Website added." : "Changes saved.");
              setFormTarget(null);
              monitors.refresh();
              if (formTarget === "new") setSiteId(saved.id);
            }}
          />
        </Drawer>
      ) : null}

      {deleting ? (
        <DeleteMonitorDialog
          monitor={deleting}
          deleting={deletingBusy}
          error={deleteError}
          onConfirm={confirmDelete}
          onClose={() => setDeleting(null)}
        />
      ) : null}
    </div>
  );
}
