import type { ComponentProps } from "react";

export type ButtonVariant = "primary" | "secondary" | "ghost";
export type ButtonSize = "sm" | "md";

const BASE =
  "inline-flex items-center justify-center gap-1.5 rounded-control font-medium whitespace-nowrap transition-[background-color,border-color,color,box-shadow] duration-100 select-none disabled:cursor-not-allowed disabled:opacity-55 aria-disabled:pointer-events-none aria-disabled:opacity-45";

const SIZES: Record<ButtonSize, string> = {
  sm: "h-7 px-2.5 text-[13px]",
  md: "h-8 px-3 text-sm",
};

export const BUTTON_VARIANTS: Record<ButtonVariant, string> = {
  primary: "bg-accent text-white shadow-[inset_0_1px_0_rgb(255_255_255/0.12)] hover:bg-accent-hover active:bg-accent-ink",
  secondary:
    "border border-border-strong bg-surface text-ink shadow-[0_1px_0_rgb(17_24_39/0.04)] hover:border-ink-muted/60 hover:bg-surface-muted active:bg-surface-hover",
  ghost: "text-ink-secondary hover:bg-surface-hover hover:text-ink active:bg-border",
};

interface ButtonProps extends ComponentProps<"button"> {
  variant?: ButtonVariant;
  size?: ButtonSize;
}

export function buttonClassName(variant: ButtonVariant = "secondary", className = "", size: ButtonSize = "md"): string {
  return `${BASE} ${SIZES[size]} ${BUTTON_VARIANTS[variant]} ${className}`;
}

export function Button({ variant = "secondary", size = "md", className = "", type = "button", ...props }: ButtonProps) {
  return <button type={type} className={buttonClassName(variant, className, size)} {...props} />;
}
