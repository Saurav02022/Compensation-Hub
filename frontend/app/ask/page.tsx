import { AskForm } from "@/components/ask-compensation/AskForm";
import { askCompensationAction } from "./actions";

const EXAMPLE_QUESTIONS = [
  "What is the average salary in Engineering?",
  "What is the total payroll for Germany?",
  "Show average compensation by department.",
  "How many Engineering employees are based in India?",
];

export default function AskPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Ask Compensation</h1>
        <p className="text-sm text-slate-600">
          Ask a compensation question in plain language. The answer is calculated from the
          employee data with the same analytics used on the overview page, and monetary values are
          shown in USD.
        </p>
      </div>
      <AskForm action={askCompensationAction} exampleQuestions={EXAMPLE_QUESTIONS} />
    </div>
  );
}
