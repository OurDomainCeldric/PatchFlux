import "./globals.css";
import type { ReactNode } from "react";
import { ThemeScript } from "@/components/ThemeScript";

export const metadata = {
  title: "PatchFlux",
  description:
    "Independent third-party aggregator for Microsoft product changes, new features, and IT news.",
  robots: { index: true, follow: true },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <ThemeScript />
      {children}
    </>
  );
}
