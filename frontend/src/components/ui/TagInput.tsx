import { useState, type KeyboardEvent } from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/cn";
import { FieldMessage } from "@/components/ui/Fields";

interface TagInputProps {
  id: string;
  label: string;
  values: string[];
  onChange: (values: string[]) => void;
  placeholder?: string;
  hint?: string;
  error?: string | null;
}

export function TagInput({ id, label, values, onChange, placeholder, hint, error }: TagInputProps) {
  const [draft, setDraft] = useState("");

  const commit = () => {
    const value = draft.trim();
    setDraft("");
    if (!value || values.includes(value)) return;
    onChange([...values, value]);
  };

  const onKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter" || event.key === ",") {
      event.preventDefault();
      commit();
    } else if (event.key === "Backspace" && draft === "" && values.length > 0) {
      onChange(values.slice(0, -1));
    }
  };

  return (
    <div className="flex min-w-0 flex-col gap-1.5">
      <label htmlFor={id} className="text-xs font-medium text-subtle">{label}</label>
      <div
        className={cn(
          "flex min-h-10 min-w-0 flex-wrap items-center gap-1.5 rounded-lg border bg-card px-2 py-1.5 focus-within:ring-2 focus-within:ring-accent focus-within:ring-offset-2 focus-within:ring-offset-page",
          error ? "border-down" : "border-line",
        )}
      >
        {values.map((value) => (
          <span key={value} className="inline-flex max-w-full items-center gap-1 rounded-md bg-hover py-0.5 pl-2 pr-1 text-xs text-ink">
            <span className="truncate">{value}</span>
            <button
              type="button"
              aria-label={`Remove ${value}`}
              onClick={() => onChange(values.filter((item) => item !== value))}
              className="ctl-square-sm inline-flex shrink-0 items-center justify-center rounded text-subtle hover:text-ink"
            >
              <X size={12} aria-hidden="true" />
            </button>
          </span>
        ))}
        <input
          id={id}
          value={draft}
          placeholder={values.length === 0 ? placeholder : undefined}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={onKeyDown}
          onBlur={commit}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? `${id}-error` : hint ? `${id}-hint` : undefined}
          className="min-w-[120px] flex-1 bg-transparent px-1 py-1 text-sm text-ink placeholder:text-muted focus:outline-none"
        />
      </div>
      <FieldMessage id={id} error={error} hint={hint} />
    </div>
  );
}
