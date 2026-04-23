"use client";

import { useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";

export type FeedTab = "news" | "community";

interface FeedTabsProps {
  pathname: string;
  activeTab: FeedTab;
}

export function FeedTabs({ pathname, activeTab }: FeedTabsProps) {
  const t = useTranslations("tabs");
  const router = useRouter();
  const searchParams = useSearchParams();

  const switchTab = useCallback(
    (tab: FeedTab) => {
      // Preserve existing params but swap the tab, and clear filters that
      // don't make sense across tabs (hot, topics stay; source/product are OK too).
      const next = new URLSearchParams(searchParams?.toString() ?? "");
      if (tab === "news") {
        next.delete("tab");
      } else {
        next.set("tab", tab);
      }
      // Clear hot filter when switching to community — priority badges don't apply.
      if (tab === "community") {
        next.delete("hot");
      }
      const qs = next.toString();
      router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    },
    [pathname, router, searchParams],
  );

  const tabs: { key: FeedTab; label: string }[] = [
    { key: "news", label: t("news") },
    { key: "community", label: t("community") },
  ];

  return (
    <nav
      aria-label={t("ariaLabel")}
      className="mb-4 flex gap-1 border-b border-zinc-200 dark:border-zinc-800"
    >
      {tabs.map(({ key, label }) => {
        const isActive = activeTab === key;
        return (
          <button
            key={key}
            type="button"
            role="tab"
            aria-selected={isActive}
            onClick={() => switchTab(key)}
            className={
              "relative px-4 py-2 text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-blue-500 " +
              (isActive
                ? "text-blue-700 dark:text-blue-400 after:absolute after:bottom-[-1px] after:left-0 after:right-0 after:h-[2px] after:rounded-t after:bg-blue-600 dark:after:bg-blue-400"
                : "text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100")
            }
          >
            {label}
            {key === "community" && (
              <span
                aria-hidden="true"
                className="ml-1.5 rounded-full bg-zinc-100 px-1.5 py-0.5 text-[10px] font-semibold text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400"
              >
                β
              </span>
            )}
          </button>
        );
      })}
    </nav>
  );
}
