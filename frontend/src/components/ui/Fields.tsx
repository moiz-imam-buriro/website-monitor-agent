import type { InputHTMLAttributes, ReactNode, SelectHTMLAttributes } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/cn";

const CONTROL =
  "ctl w-full min-w-0 rounded-lg border bg-card px-3 text-sm text-ink placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 focus:ring-offset-page disabled:opacity-50";

interface FieldProps {
  id: string;
  label: string;
  error?: string | null;
  hint?: string;
}

export function FieldMessage({ id, error, hint }: { id: string; error?: string | null; hint?: string }) {
  if (error) return <p id={`${id}-error`} className="text-xs text-down">{error}</p>;
  if (hint) return <p id={`${id}-hint`} className="text-xs text-muted">{hint}</p>;
  return null;
}

function describedBy(id: string, error?: string | null, hint?: string): string | undefined {
  if (error) return `${id}-error`;
  if (hint) return `${id}-hint`;
  return undefined;
}

export function TextField({ id, label, error, hint, className, ...input }: FieldProps & InputHTMLAttributes<HTMLInputElement>) {
  return (
    <div className="flex min-w-0 flex-col gap-1.5">
      <label htmlFor={id} className="text-xs font-medium text-subtle">{label}</label>
      <input
        id={id}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy(id, error, hint)}
        className={cn(CONTROL, error ? "border-down" : "border-line", className)}
        {...input}
      />
      <FieldMessage id={id} error={error} hint={hint} />
    </div>
  );
}

interface SelectFieldProps extends FieldProps, Omit<SelectHTMLAttributes<HTMLSelectElement>, "id"> {
  leading?: ReactNode;
}

export function SelectField({ id, label, error, hint, leading, className, children, ...select }: SelectFieldProps) {
  return (
    <div className="flex min-w-0 flex-col gap-1.5">
      <label htmlFor={id} className="text-xs font-medium text-subtle">{label}</label>
      <div className="relative min-w-0">
        {leading ? <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2">{leading}</span> : null}
        <select
          id={id}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy(id, error, hint)}
          className={cn("ctl w-full min-w-0 appearance-none pr-9", !!leading && "pl-11", error ? "border-down" : "border-line", className)}
          {...select}
        >
          {children}
        </select>
        <ChevronDown size={16} aria-hidden="true" className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-subtle" />
      </div>
      <FieldMessage id={id} error={error} hint={hint} />
    </div>
  );
}
