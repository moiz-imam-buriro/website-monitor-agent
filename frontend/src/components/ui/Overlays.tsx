import { createPortal } from "react-dom";
import { useId, useRef, type ReactNode } from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/cn";
import { useModal } from "@/hooks/useModal";
import { IconButton } from "@/components/ui/Button";

interface DrawerProps {
  title: ReactNode;
  onClose: () => void;
  children: ReactNode;
  footer?: ReactNode;
  side?: "right" | "left";
}

export function Drawer({ title, onClose, children, footer, side = "right" }: DrawerProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const titleId = useId();
  useModal(panelRef, onClose);
  const isLeft = side === "left";

  return createPortal(
    <div className="fixed inset-0 z-50">
      <div className="anim-overlay absolute inset-0 bg-overlay" onClick={onClose} aria-hidden="true" />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        className={cn(
          "absolute top-0 flex h-dvh flex-col bg-card outline-none",
          isLeft
            ? "anim-drawer-left left-0 w-[min(280px,85vw)] border-r border-line"
            : "anim-drawer right-0 w-full border-l border-line sm:w-[480px]",
        )}
      >
        <div className="flex shrink-0 items-start justify-between gap-3 border-b border-line px-5 py-4 sm:px-6">
          <div id={titleId} className="min-w-0 flex-1">{title}</div>
          <IconButton label="Close" onClick={onClose}>
            <X size={18} aria-hidden="true" />
          </IconButton>
        </div>
        <div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-5 py-5 sm:px-6">{children}</div>
        {footer ? (
          <div className="shrink-0 border-t border-line bg-card px-5 py-4 pb-[max(16px,env(safe-area-inset-bottom))] sm:px-6">
            {footer}
          </div>
        ) : null}
      </div>
    </div>,
    document.body,
  );
}

interface DialogProps {
  title: string;
  description?: string;
  onClose: () => void;
  footer: ReactNode;
}

export function Dialog({ title, description, onClose, footer }: DialogProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const titleId = useId();
  useModal(panelRef, onClose);

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="anim-overlay absolute inset-0 bg-overlay" onClick={onClose} aria-hidden="true" />
      <div
        ref={panelRef}
        role="alertdialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        className="anim-dialog relative w-[400px] max-w-[calc(100vw-32px)] rounded-xl border border-line bg-card p-5 outline-none"
      >
        <h2 id={titleId} className="text-base font-medium text-ink">{title}</h2>
        {description ? <p className="mt-2 text-sm text-subtle">{description}</p> : null}
        <div className="mt-5 flex flex-wrap justify-end gap-2">{footer}</div>
      </div>
    </div>,
    document.body,
  );
}

interface BottomSheetProps {
  title: string;
  onClose: () => void;
  children: ReactNode;
}

export function BottomSheet({ title, onClose, children }: BottomSheetProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const titleId = useId();
  useModal(panelRef, onClose);

  return createPortal(
    <div className="fixed inset-0 z-50">
      <div className="anim-overlay absolute inset-0 bg-overlay" onClick={onClose} aria-hidden="true" />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        className="anim-sheet absolute inset-x-0 bottom-0 max-h-[85dvh] overflow-y-auto rounded-t-xl border-t border-line bg-card px-4 pb-[max(16px,env(safe-area-inset-bottom))] pt-3 outline-none"
      >
        <div className="mx-auto mb-3 h-1 w-10 rounded-full bg-line" aria-hidden="true" />
        <div className="flex items-center justify-between gap-3 pb-2">
          <p id={titleId} className="min-w-0 truncate text-sm font-medium text-ink">{title}</p>
          <IconButton label="Close" onClick={onClose}>
            <X size={18} aria-hidden="true" />
          </IconButton>
        </div>
        {children}
      </div>
    </div>,
    document.body,
  );
}
