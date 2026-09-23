import { vi } from "vitest";

/** A stand-in for the App Router used by components that navigate through a shared transition. */
export const router = {
  replace: vi.fn(),
  push: vi.fn(),
  refresh: vi.fn(),
};

export function resetRouter() {
  router.replace.mockClear();
  router.push.mockClear();
  router.refresh.mockClear();
}
