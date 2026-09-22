import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Compensation Hub",
  description: "Manage current employee compensation across countries.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-50 text-slate-900">
        <header className="border-b border-slate-200 bg-white">
          <nav
            aria-label="Primary"
            className="mx-auto flex max-w-6xl items-center gap-6 px-4 py-3"
          >
            <Link href="/employees" className="text-lg font-semibold">
              Compensation Hub
            </Link>
            <Link href="/employees" className="text-sm text-slate-700 hover:underline">
              Employees
            </Link>
            <Link href="/analytics" className="text-sm text-slate-700 hover:underline">
              Analytics
            </Link>
          </nav>
        </header>
        <main className="mx-auto max-w-6xl px-4 py-6">{children}</main>
      </body>
    </html>
  );
}
