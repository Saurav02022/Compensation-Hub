/** Pages open the global assistant through this event so they need no shared state with the shell. */
export const OPEN_ASK_COMPENSATION_EVENT = "compensation-hub:open-ask";

export function openAskCompensation(): void {
  window.dispatchEvent(new CustomEvent(OPEN_ASK_COMPENSATION_EVENT));
}
