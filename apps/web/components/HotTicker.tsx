"use client";

import { useEffect, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { fetchHot, type NewsItem } from "@/lib/api";

/**
 * A horizontally scrolling ticker of the current "hot" headlines
 * (priority>=2). Items link out to the original publisher.
 *
 * - Pauses on hover / keyboard focus.
 * - Respects ``prefers-reduced-motion``: falls back to a static grid.
 * - Renders nothing when there are no hot items (to avoid empty noise).
 */
export function HotTicker() {
  const t = useTranslations();
  const locale = useLocale();
  const [items, setItems] = useState<NewsItem[] | null>(null);
  const [reduceMotion, setReduceMotion] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetchHot({ limit: 10, days: 7 })
      .then((r) => {
        if (!cancelled) setItems(r.items);
      })
      .catch(() => {
        if (!cancelled) setItems([]);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduceMotion(media.matches);
    const onChange = (e: MediaQueryListEvent) => setReduceMotion(e.matches);
    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  }, []);

  if (!items || items.length === 0) return null;

  const dateFmt = new Intl.DateTimeFormat(locale, { dateStyle: "short" });
  // Duplicate the list so the CSS scroll appears seamless.
  const stream = reduceMotion ? items : [...items, ...items];

  return (
    <section
      aria-label={t("news.hotTicker")}
      className="mb-6 overflow-hidden rounded-lg border border-red-300 bg-gradient-to-r from-red-50 to-red-100/40 dark:border-red-900/60 dark:from-red-950/40 dark:to-red-900/10"
    >
      <div className="flex items-stretch">
        <div className="flex shrink-0 items-center gap-2 border-r border-red-300/70 bg-red-600 px-3 py-2 text-xs font-bold uppercase tracking-wide text-white dark:border-red-900/70">
          <span aria-hidden>🔥</span>
          <span>{t("news.hotToday")}</span>
        </div>
        <div className="group relative flex-1 overflow-hidden">
          <ul
            className={
              reduceMotion
                ? "flex flex-wrap gap-x-6 gap-y-1 px-3 py-2 text-sm"
                : "flex w-max animate-hot-ticker gap-8 whitespace-nowrap px-3 py-2 text-sm group-hover:[animation-play-state:paused] group-focus-within:[animation-play-state:paused]"
            }
          >
            {stream.map((item, idx) => (
              <li
                key={`${item.id}-${idx}`}
                className="flex items-center gap-2"
              >
                <time
                  className="shrink-0 text-[11px] tabular-nums text-red-900/70 dark:text-red-200/70"
                  dateTime={item.publishedAt}
                >
                  {dateFmt.format(new Date(item.publishedAt))}
                </time>
                <a
                  href={item.url}
                  target="_blank"
                  rel="noopener nofollow"
                  className="font-medium text-red-900 hover:underline focus-visible:underline focus-visible:outline-2 focus-visible:outline-red-700 dark:text-red-100"
                >
                  {item.title}
                </a>
                <span className="shrink-0 text-[11px] uppercase text-red-900/60 dark:text-red-200/60">
                  {item.sourceName}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
