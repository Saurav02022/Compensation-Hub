"use client";

import Link from "next/link";
import { useEffect, useSyncExternalStore } from "react";

import { Icon } from "@/components/ui/Icon";

const STORAGE_KEY = "compensation-hub:directory-href";
const DEFAULT_HREF = "/employees";

function readDirectoryHref(): string {
  try {
    const stored = window.sessionStorage.getItem(STORAGE_KEY);
    return stored?.startsWith("/employees") ? stored : DEFAULT_HREF;
  } catch {
    return DEFAULT_HREF;
  }
}

/** Remembers the directory view (search, filters, page) so the detail page can return to it. */
export function RememberDirectory({ href }: { href: string }) {
  useEffect(() => {
    try {
      window.sessionStorage.setItem(STORAGE_KEY, href);
    } catch {
      // Storage can be unavailable (private mode, blocked site data); the back link then opens the full list.
    }
  }, [href]);
  return null;
}

const noopSubscribe = () => () => {};

export function BackToDirectory() {
  const href = useSyncExternalStore(noopSubscribe, readDirectoryHref, () => DEFAULT_HREF);
  return (
    <Link href={href} className="inline-flex items-center gap-1.5 text-[13px] text-ink-secondary hover:text-ink">
      <Icon name="back" size={14} />
      {href === DEFAULT_HREF ? "Employees" : "Back to results"}
    </Link>
  );
}
