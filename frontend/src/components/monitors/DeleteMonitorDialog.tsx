import { Dialog } from "@/components/ui/Overlays";
import { Button } from "@/components/ui/Button";
import { ErrorNotice } from "@/components/ui/ErrorNotice";
import type { Monitor } from "@/types";

interface DeleteMonitorDialogProps {
  monitor: Monitor;
  deleting: boolean;
  error: unknown;
  onConfirm: () => void;
  onClose: () => void;
}

export function DeleteMonitorDialog({ monitor, deleting, error, onConfirm, onClose }: DeleteMonitorDialogProps) {
  return (
    <Dialog
      title={`Delete ${monitor.name}?`}
      description="This stops monitoring this website and removes its check history. This cannot be undone."
      onClose={deleting ? () => undefined : onClose}
      footer={
        <>
          {error ? <div className="w-full"><ErrorNotice error={error} /></div> : null}
          <Button variant="secondary" onClick={onClose} disabled={deleting}>Cancel</Button>
          <Button variant="destructive" loading={deleting} onClick={onConfirm}>Delete website</Button>
        </>
      }
    />
  );
}
