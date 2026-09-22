import type { Metadata } from "next";
import "./globals.css";

import { AppHeader } from "@/components/shell/AppHeader";
import { askCompensationAction } from "./actions/askCompensation";

export const metadata: Metadata = {
  title: "Compensation Hub",
  description: "Manage current employee compensation across countries.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body className="min-h-screen">
        <AppHeader askAction={askCompensationAction} />
        <main className="mx-auto max-w-6xl px-4 py-6 sm:px-6">{children}</main>
      </body>
    </html>
  );
}
