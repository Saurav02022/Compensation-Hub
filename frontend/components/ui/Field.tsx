import type { ComponentProps, ReactNode } from "react";

export const CONTROL_CLASS =
  "h-9 w-full rounded-control border border-border-strong bg-surface px-3 text-sm text-ink placeholder:text-ink-muted hover:border-ink-muted focus:border-accent";

interface FieldProps {
  label: string;
  htmlFor: string;
  hint?: string;
  children: ReactNode;
  className?: string;
}

export function Field({ label, htmlFor, hint, children, className = "" }: FieldProps) {
  return (
    <div className={`flex flex-col gap-1 ${className}`}>
      <label htmlFor={htmlFor} className="text-xs font-medium text-ink-secondary">
        {label}
      </label>
      {children}
      {hint && <p className="text-xs text-ink-muted">{hint}</p>}
    </div>
  );
}

export function Input({ className = "", ...props }: ComponentProps<"input">) {
  return <input className={`${CONTROL_CLASS} ${className}`} {...props} />;
}

export function Select({ className = "", ...props }: ComponentProps<"select">) {
  return <select className={`${CONTROL_CLASS} ${className}`} {...props} />;
}

export function Textarea({ className = "", ...props }: ComponentProps<"textarea">) {
  return (
    <textarea
      className={`w-full rounded-control border border-border-strong bg-surface px-3 py-2 text-sm text-ink placeholder:text-ink-muted hover:border-ink-muted focus:border-accent ${className}`}
      {...props}
    />
  );
}
