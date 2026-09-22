"use client";

import { Button, type ButtonVariant } from "@/components/ui/Button";
import { openAskCompensation } from "./launcher";

interface AskLauncherButtonProps {
  variant?: ButtonVariant;
  children?: React.ReactNode;
  className?: string;
}

export function AskLauncherButton({ variant = "secondary", children = "Ask Compensation", className }: AskLauncherButtonProps) {
  return (
    <Button variant={variant} onClick={openAskCompensation} aria-haspopup="dialog" className={className}>
      {children}
    </Button>
  );
}
