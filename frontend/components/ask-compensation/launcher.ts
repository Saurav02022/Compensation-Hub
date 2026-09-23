/** Pages open the global assistant through this event so they need no shared state with the shell. */
export const OPEN_ASK_COMPENSATION_EVENT = "compensation-hub:open-ask";

export interface OpenAskDetail {
  /** A question to ask as soon as the assistant opens. */
  question?: string;
}

export function openAskCompensation(question?: string): void {
  window.dispatchEvent(new CustomEvent<OpenAskDetail>(OPEN_ASK_COMPENSATION_EVENT, { detail: { question } }));
}
