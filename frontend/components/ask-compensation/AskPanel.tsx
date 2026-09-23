"use client";

import { useEffect, useId, useRef, useState, type RefObject } from "react";

import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { AskMessage } from "./AskMessage";
import { MIN_QUESTION_LENGTH, type AskExchange } from "./types";

const FOCUSABLE = 'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select, [tabindex]:not([tabindex="-1"])';

export interface AskConversation {
  exchanges: AskExchange[];
  pendingQuestion: string | null;
  pending: boolean;
  ask: (question: string) => boolean;
  reset: () => void;
}

interface AskPanelProps {
  open: boolean;
  /** Docked beside the page on wide screens; a modal sheet over the page otherwise. */
  docked: boolean;
  onClose: () => void;
  conversation: AskConversation;
  suggestions: string[];
  inputRef: RefObject<HTMLTextAreaElement | null>;
}

export function AskPanel({ open, docked, onClose, conversation, suggestions, inputRef }: AskPanelProps) {
  const { exchanges, pendingQuestion, pending, ask, reset } = conversation;
  const [question, setQuestion] = useState("");
  const panelRef = useRef<HTMLDivElement>(null);
  const logRef = useRef<HTMLDivElement>(null);
  const titleId = useId();
  const descriptionId = useId();

  useEffect(() => {
    if (!open) return;
    const previouslyFocused = document.activeElement as HTMLElement | null;
    const panel = panelRef.current;
    inputRef.current?.focus();
    return () => {
      const focusInPanel = !document.activeElement || document.activeElement === document.body || panel?.contains(document.activeElement);
      if (focusInPanel && previouslyFocused?.isConnected) previouslyFocused.focus();
    };
  }, [open, inputRef]);

  useEffect(() => {
    if (!open || docked) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

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
    };
  }, [open, docked, onClose]);

  useEffect(() => {
    const log = logRef.current;
    if (log) log.scrollTop = log.scrollHeight;
  }, [exchanges.length, pendingQuestion]);

  function submit(text: string) {
    if (ask(text)) setQuestion("");
  }

  if (!open) return null;

  const canSend = !pending && question.trim().length >= MIN_QUESTION_LENGTH;
  const empty = exchanges.length === 0 && pendingQuestion === null;

  return (
    <>
      {!docked && (
        <div aria-hidden="true" onClick={onClose} className="fixed inset-0 z-40 animate-fade-in bg-ink/25" />
      )}
      <div
        ref={panelRef}
        role="dialog"
        aria-modal={docked ? undefined : true}
        aria-labelledby={titleId}
        aria-describedby={descriptionId}
        onKeyDown={(event) => {
          if (docked && event.key === "Escape") {
            event.preventDefault();
            onClose();
          }
        }}
        className={`fixed inset-y-0 right-0 z-50 flex w-full animate-panel-in flex-col bg-surface sm:w-[400px] ${
          docked ? "border-l border-border" : "shadow-panel"
        }`}
      >
        <div className="flex h-14 shrink-0 items-center justify-between gap-3 border-b border-border px-4">
          <div className="min-w-0">
            <h2 id={titleId} className="text-sm font-semibold text-ink">
              Ask Compensation
            </h2>
            <p id={descriptionId} className="truncate text-xs text-ink-muted">
              Answers grounded in Compensation Hub data
            </p>
          </div>
          <div className="flex items-center gap-1">
            {exchanges.length > 0 && (
              <Button variant="ghost" size="sm" onClick={reset} disabled={pending}>
                Clear
              </Button>
            )}
            <Button variant="ghost" size="sm" onClick={onClose} aria-label="Close Ask Compensation" className="w-7 px-0">
              <Icon name="close" />
            </Button>
          </div>
        </div>

        <div ref={logRef} role="log" aria-live="polite" className="flex-1 space-y-5 overflow-y-auto px-4 py-4">
          {empty && (
            <div>
              <p className="text-[13px] text-ink-secondary">
                Ask any read-only question about the data in Compensation Hub. If the required data is available, the
                answer is derived from it. If it is not, the assistant explains what is missing.
              </p>
              <p className="mt-5 text-xs font-medium text-ink-muted">Examples</p>
              <ul className="mt-1.5 divide-y divide-border rounded-surface border border-border">
                {suggestions.map((suggestion) => (
                  <li key={suggestion}>
                    <button
                      type="button"
                      onClick={() => submit(suggestion)}
                      className="group flex w-full items-center justify-between gap-3 px-3 py-2.5 text-left text-[13px] text-ink first:rounded-t-surface last:rounded-b-surface hover:bg-surface-muted"
                    >
                      {suggestion}
                      <Icon name="arrowRight" size={14} className="text-ink-muted opacity-0 transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100" />
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {exchanges.map((exchange) => (
            <AskMessage key={exchange.id} exchange={exchange} onRetry={submit} />
          ))}
          {pendingQuestion !== null && (
            <div className="flex flex-col gap-2">
              <p className="ml-10 self-end rounded-surface bg-surface-hover px-3 py-2 text-[13px] text-ink">{pendingQuestion}</p>
              <div className="rounded-surface border border-border px-3.5 py-3">
                <p role="status" className="text-[13px] text-ink-muted">
                  Working out the answer…
                </p>
                <div aria-hidden="true" className="mt-2.5 space-y-2">
                  <div className="h-2.5 w-2/3 animate-pulse rounded bg-surface-hover" />
                  <div className="h-2.5 w-2/5 animate-pulse rounded bg-surface-hover" />
                </div>
              </div>
            </div>
          )}
        </div>

        <form
          onSubmit={(event) => {
            event.preventDefault();
            submit(question);
          }}
          className="shrink-0 border-t border-border px-4 pt-3 pb-3"
        >
          <label htmlFor="ask-question" className="sr-only">
            Question
          </label>
          <div className="relative rounded-surface border border-border-strong bg-surface transition-colors focus-within:border-accent focus-within:ring-3 focus-within:ring-accent/15">
            <textarea
              id="ask-question"
              ref={inputRef}
              name="question"
              rows={2}
              value={question}
              maxLength={500}
              placeholder="Ask a compensation question"
              onChange={(event) => setQuestion(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
                  event.preventDefault();
                  submit(question);
                }
              }}
              className="block max-h-36 min-h-[3.25rem] w-full resize-none bg-transparent py-2.5 pr-12 pl-3 text-sm text-ink [field-sizing:content] placeholder:text-ink-muted focus:outline-none focus-visible:outline-none"
            />
            <Button
              type="submit"
              variant="primary"
              size="sm"
              disabled={!canSend}
              aria-label={pending ? "Asking" : "Ask"}
              className="absolute right-2 bottom-2 w-7 px-0"
            >
              <Icon name="arrowUp" size={15} />
            </Button>
          </div>
          <p className="mt-1.5 text-[11px] text-ink-muted">Enter to ask · Shift+Enter for a new line</p>
        </form>
      </div>
    </>
  );
}
