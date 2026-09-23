"use client";

import { useRouter } from "next/navigation";
import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useTransition,
  type ComponentProps,
  type MouseEvent,
  type ReactNode,
} from "react";

import { RefreshBar } from "./States";

interface RouteTransitionValue {
  pending: boolean;
  replace: (href: string) => void;
  push: (href: string) => void;
}

const RouteTransitionContext = createContext<RouteTransitionValue | null>(null);

/**
 * Shares one navigation transition between the controls that change a page's URL state and the
 * content they refresh, so the current results stay on screen, dimmed, until the new ones arrive.
 */
export function RouteTransitionProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();

  const replace = useCallback(
    (href: string) => startTransition(() => router.replace(href, { scroll: false })),
    [router],
  );
  const push = useCallback((href: string) => startTransition(() => router.push(href)), [router]);
  const value = useMemo(() => ({ pending, replace, push }), [pending, replace, push]);

  return <RouteTransitionContext.Provider value={value}>{children}</RouteTransitionContext.Provider>;
}

export function useRouteTransition(): RouteTransitionValue {
  const value = useContext(RouteTransitionContext);
  if (!value) throw new Error("useRouteTransition must be used inside RouteTransitionProvider");
  return value;
}

/** Content that dims while a transition started by a sibling control is in flight. */
export function PendingContent({ children, className = "" }: { children: ReactNode; className?: string }) {
  const { pending } = useRouteTransition();
  return (
    <div aria-busy={pending} className="relative">
      <div className="absolute inset-x-0 -top-2">
        <RefreshBar active={pending} />
      </div>
      <div className={`transition-opacity duration-150 ${pending ? "opacity-55" : ""} ${className}`}>{children}</div>
    </div>
  );
}

/**
 * A link that navigates inside the shared transition. It stays a real link, so it can be opened
 * in a new tab and works before hydration.
 */
export function TransitionLink({
  href,
  children,
  className,
  ...props
}: { href: string; children: ReactNode; className?: string } & Omit<ComponentProps<"a">, "href">) {
  const { push } = useRouteTransition();

  function onClick(event: MouseEvent<HTMLAnchorElement>) {
    if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    push(href);
  }

  return (
    <a href={href} onClick={onClick} className={className} {...props}>
      {children}
    </a>
  );
}
