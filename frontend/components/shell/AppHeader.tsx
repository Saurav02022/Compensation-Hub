"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { AskDrawer, type AskAction, type AskExchange } from "@/components/ask-compensation/AskDrawer";
import { OPEN_ASK_COMPENSATION_EVENT } from "@/components/ask-compensation/launcher";
import { Button } from "@/components/ui/Button";

const NAVIGATION = [
  { href: "/", label: "Overview" },
  { href: "/employees", label: "Employees" },
  { href: "/analytics", label: "Analytics" },
] as const;

const SUGGESTED_QUESTIONS = [
  "What is the average salary in Engineering?",
  "What is the total payroll in Germany?",
  "Compare average salary by department.",
  "How many employees are in India?",
  "Which three countries have the highest payroll?",
];

function isActive(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`);
}

interface AppHeaderProps {
  askAction: AskAction;
}

export function AppHeader({ askAction }: AppHeaderProps) {
  const pathname = usePathname();
  const [assistantOpen, setAssistantOpen] = useState(false);
  const [exchanges, setExchanges] = useState<AskExchange[]>([]);
  const closeAssistant = useCallback(() => setAssistantOpen(false), []);

  useEffect(() => {
    const open = () => setAssistantOpen(true);
    window.addEventListener(OPEN_ASK_COMPENSATION_EVENT, open);
    return () => window.removeEventListener(OPEN_ASK_COMPENSATION_EVENT, open);
  }, []);

  return (
    <>
      <header className="sticky top-0 z-30 border-b border-border bg-surface">
        <div className="mx-auto flex h-14 max-w-6xl items-center gap-6 px-4 sm:px-6">
          <Link href="/" className="text-sm font-semibold tracking-tight text-ink">
            Compensation Hub
          </Link>
          <nav aria-label="Primary" className="flex h-full items-stretch gap-1">
            {NAVIGATION.map((item) => {
              const active = isActive(pathname, item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  className={`relative flex items-center px-2 text-sm transition-colors ${
                    active ? "font-medium text-ink" : "text-ink-secondary hover:text-ink"
                  }`}
                >
                  {item.label}
                  {active && <span aria-hidden="true" className="absolute inset-x-2 bottom-0 h-0.5 bg-accent" />}
                </Link>
              );
            })}
          </nav>
          <div className="ml-auto">
            <Button
              variant="secondary"
              onClick={() => setAssistantOpen(true)}
              aria-haspopup="dialog"
              aria-expanded={assistantOpen}
            >
              <span aria-hidden="true" className="h-2 w-2 rounded-full bg-accent" />
              Ask Compensation
            </Button>
          </div>
        </div>
      </header>
      <AskDrawer
        open={assistantOpen}
        onClose={closeAssistant}
        action={askAction}
        exchanges={exchanges}
        onExchange={(exchange) => setExchanges((current) => [...current, exchange])}
        suggestions={SUGGESTED_QUESTIONS}
      />
    </>
  );
}
