import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

import { AppShell } from "@/components/shell/AppShell";
import { askCompensationAction } from "./actions/askCompensation";

const geistSans = Geist({ subsets: ["latin"], variable: "--font-geist-sans" });
const geistMono = Geist_Mono({ subsets: ["latin"], variable: "--font-geist-mono" });

export const metadata: Metadata = {
  title: { default: "Compensation Hub", template: "%s · Compensation Hub" },
  description: "Manage current employee compensation across countries.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable}`}>
      <body>
        <AppShell askAction={askCompensationAction}>{children}</AppShell>
      </body>
    </html>
  );
}
