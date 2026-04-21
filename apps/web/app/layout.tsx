import "./globals.css";
import type { ReactNode } from "react";

export const metadata = {
  title: "OmlorsNewsBot",
  description:
    "Independent third-party aggregator for Microsoft product changes, new features, and IT news.",
  robots: { index: true, follow: true },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return children;
}
