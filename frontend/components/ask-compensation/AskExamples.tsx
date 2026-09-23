"use client";

import { Icon } from "@/components/ui/Icon";
import { openAskCompensation } from "./launcher";

/** Example questions that open the assistant and ask straight away. */
export function AskExamples({ questions }: { questions: string[] }) {
  return (
    <ul className="flex flex-wrap gap-2">
      {questions.map((question) => (
        <li key={question}>
          <button
            type="button"
            onClick={() => openAskCompensation(question)}
            aria-haspopup="dialog"
            className="group inline-flex min-h-8 items-center gap-2 rounded-control border border-border bg-surface px-3 py-1.5 text-left text-[13px] text-ink transition-colors hover:border-border-strong hover:bg-surface-muted"
          >
            {question}
            <Icon name="arrowRight" size={13} className="text-ink-muted transition-transform group-hover:translate-x-0.5" />
          </button>
        </li>
      ))}
    </ul>
  );
}
