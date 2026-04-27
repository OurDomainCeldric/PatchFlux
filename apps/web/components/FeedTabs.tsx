"use client";

import { useCallback, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";

export type FeedTab = "news" | "community";
export const COMMUNITY_TAB_ENABLED = false;

interface FeedTabsProps {
  pathname: string;
}

export function FeedTabs({ pathname }: FeedTabsProps) {
  const t = useTranslations("tabs");
  const router = useRouter();
  const searchParams = useSearchParams();

  const rawTab = searchParams?.get("tab");
  const activeTab: FeedTab = rawTab === "community" ? "community" : "news";

  useEffect(() => {
    if (rawTab === "community" && !COMMUNITY_TAB_ENABLED) {
      const next = new URLSearchParams(searchParams?.toString() ?? "");
      next.delete("tab");
      next.delete("hot");
      const qs = next.toString();
      router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    }
  }, [pathname, rawTab, router, searchParams]);

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

  if (!COMMUNITY_TAB_ENABLED) {
    return null;
  }

  return (
    <nav
      aria-label={t("ariaLabel")}
      className="mb-4 sm:mb-6 flex w-fit gap-1 rounded-full border border-slate-200/60 bg-slate-100/50 p-1 shadow-sm dark:border-slate-800/60 dark:bg-[#18181b]/50"
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
              "relative rounded-full px-4 py-1.5 sm:px-5 sm:py-2 text-sm font-semibold transition-all duration-300 focus-visible:outline-2 focus-visible:outline-indigo-500 " +
              (isActive
                ? "bg-white text-indigo-600 shadow-sm ring-1 ring-slate-200/50 dark:bg-slate-800 dark:text-indigo-400 dark:ring-slate-700/50"
                : "text-slate-500 hover:bg-slate-200/50 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800/50 dark:hover:text-slate-100")
            }
          >
            {label}
          </button>
        );
      })}
    </nav>
  );
}
