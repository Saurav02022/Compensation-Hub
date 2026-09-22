"use client";

import { useEffect, useId, useRef, useState, useTransition } from "react";

import { Button } from "@/components/ui/Button";
import { Textarea } from "@/components/ui/Field";
import type { AskResponse } from "@/types/ask";
import { AskMessage } from "./AskMessage";

export type AskOutcome =
  | { status: "answered"; response: AskResponse }
  | { status: "unavailable"; message: string }
  | { status: "error"; message: string };

export type AskAction = (question: string) => Promise<AskOutcome>;

export interface AskExchange {
  id: number;
  question: string;
  outcome: AskOutcome;
}

interface AskDrawerProps {
  open: boolean;
  onClose: () => void;
  action: AskAction;
  exchanges: AskExchange[];
  onExchange: (exchange: AskExchange) => void;
  suggestions: string[];
}

const FOCUSABLE = 'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])';

export function AskDrawer({ open, onClose, action, exchanges, onExchange, suggestions }: AskDrawerProps) {
  const [question, setQuestion] = useState("");
  const [pending, startTransition] = useTransition();
  const [pendingQuestion, setPendingQuestion] = useState<string | null>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const logRef = useRef<HTMLDivElement>(null);
  const titleId = useId();
  const descriptionId = useId();

  useEffect(() => {
    if (!open) return;
    const previouslyFocused = document.activeElement as HTMLElement | null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    inputRef.current?.focus();

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
        return;
      }
      if (event.key !== "Tab" || !panelRef.current) return;
      const focusable = Array.from(panelRef.current.querySelectorAll<HTMLElement>(FOCUSABLE));
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }

    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = previousOverflow;
      previouslyFocused?.focus();
    };
  }, [open, onClose]);

  useEffect(() => {
    const log = logRef.current;
    if (log) log.scrollTop = log.scrollHeight;
  }, [exchanges.length, pendingQuestion]);

  function submit(text: string) {
    const trimmed = text.trim();
    if (trimmed.length < 3 || pending) return;
    setQuestion("");
    setPendingQuestion(trimmed);
    startTransition(async () => {
      const outcome = await action(trimmed);
      onExchange({ id: Date.now(), question: trimmed, outcome });
      setPendingQuestion(null);
    });
  }

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-40">
      <button
        type="button"
        aria-label="Close Ask Compensation"
        onClick={onClose}
        className="absolute inset-0 bg-ink/30"
      />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={descriptionId}
        className="absolute inset-y-0 right-0 flex w-full max-w-md flex-col border-l border-border bg-surface shadow-xl"
      >
        <div className="flex items-start justify-between gap-3 border-b border-border px-4 py-3">
          <div>
            <h2 id={titleId} className="text-base font-semibold text-ink">
              Ask Compensation
            </h2>
            <p id={descriptionId} className="mt-0.5 text-xs text-ink-secondary">
              Answers come from the same analytics as the overview. Organization-wide amounts are in USD.
            </p>
          </div>
          <Button variant="ghost" onClick={onClose} aria-label="Close" className="h-8 px-2">
            Close
          </Button>
        </div>

        <div ref={logRef} className="flex-1 space-y-4 overflow-y-auto px-4 py-4">
          {exchanges.length === 0 && pendingQuestion === null && (
            <div>
              <p className="text-sm text-ink-secondary">
                Ask about headcount, average salary, or total payroll, filtered or grouped by country,
                department, or job title.
              </p>
              <p className="mt-3 text-xs font-medium text-ink-secondary">Try one of these</p>
              <ul className="mt-2 flex flex-wrap gap-2">
                {suggestions.map((suggestion) => (
                  <li key={suggestion}>
                    <button
                      type="button"
                      onClick={() => submit(suggestion)}
                      className="rounded-full border border-border-strong bg-surface px-3 py-1.5 text-left text-xs text-ink hover:bg-surface-muted"
                    >
                      {suggestion}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {exchanges.map((exchange) => (
            <AskMessage key={exchange.id} exchange={exchange} />
          ))}
          {pendingQuestion !== null && (
            <div className="space-y-2">
              <p className="ml-8 rounded-surface bg-accent-soft px-3 py-2 text-sm text-ink">{pendingQuestion}</p>
              <p role="status" className="text-sm text-ink-muted">
                Working out the answer…
              </p>
            </div>
          )}
        </div>

        <form
          onSubmit={(event) => {
            event.preventDefault();
            submit(question);
          }}
          className="border-t border-border px-4 py-3"
        >
          <label htmlFor="ask-question" className="sr-only">
            Question
          </label>
          <Textarea
            id="ask-question"
            ref={inputRef}
            name="question"
            rows={2}
            value={question}
            maxLength={500}
            placeholder="For example: What is the average salary in Engineering?"
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                submit(question);
              }
            }}
          />
          <div className="mt-2 flex items-center justify-between gap-3">
            <p className="text-xs text-ink-muted">Enter to send, Shift+Enter for a new line.</p>
            <Button type="submit" variant="primary" disabled={pending || question.trim().length < 3}>
              {pending ? "Asking…" : "Ask"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
