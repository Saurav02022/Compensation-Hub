import type { ComponentProps } from "react";

export type ButtonVariant = "primary" | "secondary" | "ghost";

const BASE =
  "inline-flex h-9 items-center justify-center gap-2 rounded-control px-3 text-sm font-medium whitespace-nowrap transition-colors disabled:cursor-not-allowed disabled:opacity-60";

export const BUTTON_VARIANTS: Record<ButtonVariant, string> = {
  primary: "bg-accent text-white hover:bg-accent-hover",
  secondary: "border border-border-strong bg-surface text-ink hover:bg-surface-muted",
  ghost: "text-ink-secondary hover:bg-surface-muted hover:text-ink",
};

interface ButtonProps extends ComponentProps<"button"> {
  variant?: ButtonVariant;
}

export function Button({ variant = "secondary", className = "", type = "button", ...props }: ButtonProps) {
  return <button type={type} className={`${BASE} ${BUTTON_VARIANTS[variant]} ${className}`} {...props} />;
}

export function buttonClassName(variant: ButtonVariant = "secondary", className = ""): string {
  return `${BASE} ${BUTTON_VARIANTS[variant]} ${className}`;
}
