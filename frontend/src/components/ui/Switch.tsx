import { cn } from "@/lib/cn";

interface SwitchProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label: string;
  disabled?: boolean;
}

export function Switch({ checked, onChange, label, disabled }: SwitchProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className="switch-hit inline-flex shrink-0 items-center justify-center rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-page disabled:opacity-50"
    >
      <span className={cn("relative inline-flex h-5 w-9 items-center rounded-full border transition-colors duration-150", checked ? "border-accent bg-accent" : "border-line bg-hover")}>
        <span
          aria-hidden="true"
          className={cn("absolute left-px size-4 rounded-full transition-transform duration-150", checked ? "translate-x-4 bg-accent-ink" : "translate-x-0 bg-subtle")}
        />
      </span>
    </button>
  );
}
