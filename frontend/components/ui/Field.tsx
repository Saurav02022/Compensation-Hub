import type { ComponentProps, ReactNode } from "react";

export const CONTROL_CLASS =
  "h-9 w-full rounded-control border border-border-strong bg-surface px-3 text-sm text-ink shadow-[0_1px_0_rgb(17_24_39/0.03)] transition-colors placeholder:text-ink-muted hover:border-ink-muted/60 focus:border-accent focus:outline-none focus-visible:outline-none focus:ring-3 focus:ring-accent/15 aria-invalid:border-negative-ink aria-invalid:focus:ring-negative-ink/15";

interface FieldProps {
  label: string;
  htmlFor: string;
  hint?: ReactNode;
  error?: string;
  errorId?: string;
  children: ReactNode;
  className?: string;
}

export function Field({ label, htmlFor, hint, error, errorId, children, className = "" }: FieldProps) {
  return (
    <div className={`flex flex-col gap-1.5 ${className}`}>
      <label htmlFor={htmlFor} className="text-[13px] font-medium text-ink">
        {label}
      </label>
      {children}
      {error ? (
        <p id={errorId} className="text-xs text-negative-ink">
          {error}
        </p>
      ) : (
        hint && <p className="text-xs text-ink-muted">{hint}</p>
      )}
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
      className={`${CONTROL_CLASS} h-auto resize-none py-2 leading-snug ${className}`}
      {...props}
    />
  );
}

export function Kbd({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <kbd
      className={`inline-flex h-5 min-w-5 items-center justify-center rounded border border-border-strong bg-surface px-1 font-sans text-[11px] font-medium text-ink-muted ${className}`}
    >
      {children}
    </kbd>
  );
}
