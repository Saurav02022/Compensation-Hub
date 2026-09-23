"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useRef, useState, useSyncExternalStore, type ReactNode } from "react";

import { AskPanel } from "@/components/ask-compensation/AskPanel";
import { OPEN_ASK_COMPENSATION_EVENT, type OpenAskDetail } from "@/components/ask-compensation/launcher";
import type { AskAction } from "@/components/ask-compensation/types";
import { useAskConversation } from "@/components/ask-compensation/useAskConversation";
import { Kbd } from "@/components/ui/Field";
import { Icon, type IconName } from "@/components/ui/Icon";

const NAVIGATION: { href: string; label: string; icon: IconName }[] = [
  { href: "/", label: "Overview", icon: "overview" },
  { href: "/employees", label: "Employees", icon: "employees" },
  { href: "/analytics", label: "Analytics", icon: "analytics" },
];

export const SUGGESTED_QUESTIONS = [
  "What is the total payroll in Germany?",
  "Who are the five highest-paid Engineering employees in India?",
  "What percentage of employees are in Engineering?",
  "What currencies are used in Germany?",
  "Which three countries have the highest payroll?",
];

/** The panel docks beside the page from this width; below it, it opens as a sheet over the page. */
const DOCKED_QUERY = "(min-width: 1280px)";

function isActive(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`);
}

function subscribeToMedia(query: string) {
  return (onChange: () => void) => {
    const media = window.matchMedia(query);
    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  };
}

const subscribeDocked = subscribeToMedia(DOCKED_QUERY);
const noopSubscribe = () => () => {};

function useDocked(): boolean {
  return useSyncExternalStore(subscribeDocked, () => window.matchMedia(DOCKED_QUERY).matches, () => false);
}

function useShortcutLabel(): string {
  return useSyncExternalStore(
    noopSubscribe,
    () => (/Mac|iPhone|iPad/.test(navigator.platform) ? "⌘K" : "Ctrl K"),
    () => "Ctrl K",
  );
}

function Mark() {
  return (
    <span aria-hidden="true" className="flex h-6 w-6 items-center justify-center rounded-[5px] bg-ink">
      <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
        <rect x="2" y="3" width="10" height="2" rx="1" fill="white" />
        <rect x="2" y="6.25" width="7" height="2" rx="1" fill="white" opacity="0.8" />
        <rect x="2" y="9.5" width="4" height="2" rx="1" fill="white" opacity="0.6" />
      </svg>
    </span>
  );
}

interface AppShellProps {
  askAction: AskAction;
  children: ReactNode;
}

export function AppShell({ askAction, children }: AppShellProps) {
  const pathname = usePathname();
  const docked = useDocked();
  const shortcut = useShortcutLabel();
  const [askOpen, setAskOpen] = useState(false);
  const conversation = useAskConversation(askAction);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const { ask } = conversation;

  const closeAsk = useCallback(() => setAskOpen(false), []);

  useEffect(() => {
    function onOpen(event: Event) {
      setAskOpen(true);
      const question = (event as CustomEvent<OpenAskDetail>).detail?.question;
      if (question) ask(question);
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key.toLowerCase() !== "k" || !(event.metaKey || event.ctrlKey) || event.altKey || event.shiftKey) return;
      event.preventDefault();
      const input = inputRef.current;
      if (input && document.activeElement !== input) {
        setAskOpen(true);
        input.focus();
      } else {
        setAskOpen((open) => !open);
      }
    }
    window.addEventListener(OPEN_ASK_COMPENSATION_EVENT, onOpen);
    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener(OPEN_ASK_COMPENSATION_EVENT, onOpen);
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [ask]);

  const askButton = (compact: boolean) => (
    <button
      type="button"
      onClick={() => (askOpen ? inputRef.current?.focus() : setAskOpen(true))}
      aria-haspopup="dialog"
      aria-expanded={askOpen}
      aria-keyshortcuts="Control+K Meta+K"
      className={
        compact
          ? "flex h-8 items-center gap-1.5 rounded-control border border-border-strong bg-surface px-2.5 text-[13px] font-medium text-ink hover:bg-surface-muted"
          : `flex h-8 w-full items-center gap-2.5 rounded-control px-2.5 text-[13px] font-medium transition-colors ${
              askOpen ? "bg-surface text-ink shadow-[0_0_0_1px_var(--color-border)]" : "text-ink-secondary hover:bg-ink/[0.04] hover:text-ink"
            }`
      }
    >
      <Icon name="ask" className={compact ? "text-accent" : askOpen ? "text-accent" : "text-ink-muted"} />
      <span className={compact ? "sr-only sm:not-sr-only" : "flex-1 text-left whitespace-nowrap"}>Ask Compensation</span>
      {!compact && <Kbd>{shortcut}</Kbd>}
    </button>
  );

  return (
    <div className="min-h-dvh lg:flex">
      <a
        href="#main"
        className="sr-only z-[60] rounded-control bg-ink px-3 py-2 text-sm text-white focus:not-sr-only focus:fixed focus:top-2 focus:left-2"
      >
        Skip to content
      </a>

      <aside className="sticky top-0 hidden h-dvh w-60 shrink-0 flex-col border-r border-border bg-canvas lg:flex">
        <Link href="/" className="flex h-14 items-center gap-2.5 px-4 text-sm font-semibold tracking-[-0.01em] text-ink">
          <Mark />
          Compensation Hub
        </Link>
        <nav aria-label="Primary" className="px-2.5 pt-2">
          <ul className="space-y-0.5">
            {NAVIGATION.map((item) => {
              const active = isActive(pathname, item.href);
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    aria-current={active ? "page" : undefined}
                    className={`flex h-8 items-center gap-2.5 rounded-control px-2.5 text-[13px] transition-colors ${
                      active
                        ? "bg-surface font-medium text-ink shadow-[0_0_0_1px_var(--color-border),0_1px_2px_rgb(17_24_39/0.04)]"
                        : "text-ink-secondary hover:bg-ink/[0.04] hover:text-ink"
                    }`}
                  >
                    <Icon name={item.icon} className={active ? "text-accent" : "text-ink-muted"} />
                    {item.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
        <div className="mx-2.5 mt-4 border-t border-border pt-4">{askButton(false)}</div>
        <p className="mt-auto px-4 pb-4 text-[11px] leading-4 text-ink-muted">
          Salaries in local currency. Organization figures in USD at fixed exchange rates.
        </p>
      </aside>

      <header className="sticky top-0 z-30 border-b border-border bg-surface/95 backdrop-blur supports-[backdrop-filter]:bg-surface/85 lg:hidden">
        <div className="flex h-12 items-center gap-3 px-4">
          <Link href="/" aria-label="Compensation Hub overview" className="flex items-center gap-2 text-sm font-semibold text-ink">
            <Mark />
            <span className="hidden md:inline">Compensation Hub</span>
          </Link>
          <nav aria-label="Primary" className="flex min-w-0 flex-1 items-stretch self-stretch">
            {NAVIGATION.map((item) => {
              const active = isActive(pathname, item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  className={`relative flex items-center px-2.5 text-[13px] ${
                    active ? "font-medium text-ink" : "text-ink-secondary hover:text-ink"
                  }`}
                >
                  {item.label}
                  {active && <span aria-hidden="true" className="absolute inset-x-2.5 bottom-0 h-0.5 rounded-full bg-accent" />}
                </Link>
              );
            })}
          </nav>
          {askButton(true)}
        </div>
      </header>

      <div className={`min-w-0 flex-1 transition-[margin] duration-150 ${askOpen && docked ? "mr-[400px]" : ""}`}>
        <main id="main" tabIndex={-1} className="mx-auto w-full max-w-[1160px] px-4 pt-5 pb-12 focus:outline-none sm:px-6 lg:px-10 lg:pt-8">
          {children}
        </main>
      </div>

      <AskPanel
        open={askOpen}
        docked={docked}
        onClose={closeAsk}
        conversation={conversation}
        suggestions={SUGGESTED_QUESTIONS}
        inputRef={inputRef}
      />
    </div>
  );
}
