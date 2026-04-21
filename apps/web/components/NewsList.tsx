"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { fetchNews, type NewsItem } from "@/lib/api";
import { filtersToQuery, readFiltersFromParams } from "@/components/FilterBar";

const PAGE_SIZE = 50;

interface NewsListProps {
  pathname: string;
}

function groupByDate(items: NewsItem[], formatter: Intl.DateTimeFormat) {
  const groups = new Map<string, NewsItem[]>();
  for (const item of items) {
    const d = new Date(item.publishedAt);
    const key = formatter.format(d);
    const bucket = groups.get(key);
    if (bucket) bucket.push(item);
    else groups.set(key, [item]);
  }
  return Array.from(groups.entries());
}

export function NewsList({ pathname }: NewsListProps) {
  const t = useTranslations();
  const locale = useLocale();
  const router = useRouter();
  const searchParams = useSearchParams();

  const filters = useMemo(
    () => readFiltersFromParams(searchParams ?? new URLSearchParams()),
    [searchParams],
  );

  const [items, setItems] = useState<NewsItem[] | null>(null);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const requestIdRef = useRef(0);

  const fetchOptions = useMemo(() => {
    const opts: Parameters<typeof fetchNews>[0] = { limit: PAGE_SIZE };
    if (filters.source) opts.source = filters.source;
    if (filters.product) opts.product = filters.product;
    if (filters.lang === "de" || filters.lang === "en") opts.lang = filters.lang;
    if (filters.since) opts.since = filters.since;
    if (filters.q) opts.q = filters.q;
    if (filters.deduped) opts.deduped = true;
    if (filters.onlyHot) opts.hot = true;
    return opts;
  }, [filters]);

  useEffect(() => {
    const requestId = ++requestIdRef.current;
    setItems(null);
    setNextCursor(null);
    setError(null);
    fetchNews(fetchOptions)
      .then((response) => {
        if (requestIdRef.current !== requestId) return;
        setItems(response.items);
        setNextCursor(response.nextCursor);
      })
      .catch((err: unknown) => {
        if (requestIdRef.current !== requestId) return;
        setError(err instanceof Error ? err.message : String(err));
      });
  }, [fetchOptions]);

  const loadMore = useCallback(async () => {
    if (!nextCursor || loadingMore) return;
    setLoadingMore(true);
    try {
      const response = await fetchNews({ ...fetchOptions, cursor: nextCursor });
      setItems((prev) => [...(prev ?? []), ...response.items]);
      setNextCursor(response.nextCursor);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoadingMore(false);
    }
  }, [nextCursor, loadingMore, fetchOptions]);

  const applyFilterChange = useCallback(
    (patch: Partial<ReturnType<typeof readFiltersFromParams>>) => {
      const next = filtersToQuery({ ...filters, ...patch });
      const qs = next.toString();
      router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    },
    [filters, pathname, router],
  );

  const dateHeaderFormatter = useMemo(
    () => new Intl.DateTimeFormat(locale, { dateStyle: "full" }),
    [locale],
  );
  const timeFormatter = useMemo(
    () => new Intl.DateTimeFormat(locale, { timeStyle: "short" }),
    [locale],
  );

  if (error) {
    return (
      <div
        role="alert"
        className="rounded border border-red-300 bg-red-50 p-4 text-sm text-red-900 dark:border-red-800 dark:bg-red-950/40 dark:text-red-200"
      >
        <p className="font-medium">{t("news.loadError")}</p>
        <button
          type="button"
          onClick={() => {
            setError(null);
            requestIdRef.current++;
            setItems(null);
            fetchNews(fetchOptions)
              .then((response) => {
                setItems(response.items);
                setNextCursor(response.nextCursor);
              })
              .catch((err: unknown) =>
                setError(err instanceof Error ? err.message : String(err)),
              );
          }}
          className="mt-2 rounded border border-red-300 px-3 py-1 text-xs hover:bg-red-100 dark:border-red-800 dark:hover:bg-red-900/40"
        >
          {t("news.retry")}
        </button>
      </div>
    );
  }

  if (items === null) {
    return (
      <p aria-live="polite" className="text-sm text-zinc-500">
        {t("news.loading")}
      </p>
    );
  }

  if (items.length === 0) {
    return (
      <p aria-live="polite" className="text-sm text-zinc-500">
        {t("news.empty")}
      </p>
    );
  }

  const grouped = groupByDate(items, dateHeaderFormatter);

  return (
    <div>
      <p
        aria-live="polite"
        className="mb-3 text-xs text-zinc-500 dark:text-zinc-400"
      >
        {t("news.resultCount", { count: items.length })}
      </p>
      {grouped.map(([dateLabel, bucket]) => (
        <section key={dateLabel} className="mb-6">
          <h2 className="sticky top-0 z-10 -mx-4 mb-2 bg-zinc-50/90 px-4 py-1 text-xs font-semibold uppercase tracking-wide text-zinc-600 backdrop-blur dark:bg-zinc-950/80 dark:text-zinc-300">
            {dateLabel}
          </h2>
          <ul className="space-y-3">
            {bucket.map((item) => {
              const hot = item.priority >= 2;
              const notable = item.priority === 1;
              return (
              <li
                key={item.id}
                className={
                  hot
                    ? "rounded-lg border-l-4 border-red-500 border-y border-r border-y-red-200 border-r-red-200 bg-red-50 p-4 shadow-sm transition hover:shadow-md dark:border-y-red-900 dark:border-r-red-900 dark:bg-red-950/30"
                    : notable
                    ? "rounded-lg border-l-4 border-amber-400 border-y border-r border-y-amber-200 border-r-amber-200 bg-amber-50/50 p-4 shadow-sm transition hover:shadow-md dark:border-y-amber-900 dark:border-r-amber-900 dark:bg-amber-950/20"
                    : "rounded-lg border border-zinc-200 bg-white p-4 shadow-sm transition hover:shadow-md dark:border-zinc-800 dark:bg-zinc-900"
                }
              >
                <div className="flex items-start justify-between gap-4">
                  <h3 className="flex items-start gap-2 text-base font-medium leading-snug">
                    {hot && (
                      <span
                        aria-label={t("news.hotAria")}
                        title={t("news.hotAria")}
                        className="mt-0.5 inline-flex shrink-0 items-center rounded bg-red-600 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-white"
                      >
                        {t("news.hotBadge")}
                      </span>
                    )}
                    <a
                      href={item.url}
                      target="_blank"
                      rel="noopener nofollow"
                      className="hover:underline focus-visible:underline focus-visible:outline-2 focus-visible:outline-blue-500"
                      aria-label={t("news.openOriginalAria", { source: item.sourceName })}
                    >
                      {item.title}
                    </a>
                  </h3>
                  <button
                    type="button"
                    onClick={() => applyFilterChange({ source: item.sourceId })}
                    className="shrink-0 rounded border border-zinc-300 px-2 py-0.5 text-xs uppercase text-zinc-600 hover:bg-zinc-50 focus-visible:outline-2 focus-visible:outline-blue-500 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800"
                    title={item.sourceId}
                  >
                    {item.sourceName}
                  </button>
                </div>
                <p className="mt-1 flex flex-wrap items-center gap-2 text-xs text-zinc-500">
                  <span>
                    {t("news.publishedAt", {
                      date: timeFormatter.format(new Date(item.publishedAt)),
                    })}
                    {item.author ? ` · ${item.author}` : ""}
                  </span>
                  <span
                    className="inline-flex items-center rounded border border-zinc-300 px-1.5 py-0 text-[10px] font-semibold uppercase text-zinc-600 dark:border-zinc-700 dark:text-zinc-300"
                    title={t("news.contentLanguage")}
                  >
                    {item.language}
                  </span>
                </p>
                {item.products.length > 0 && (
                  <ul className="mt-2 flex flex-wrap gap-1">
                    {item.products.map((product) => (
                      <li key={product}>
                        <button
                          type="button"
                          onClick={() => applyFilterChange({ product })}
                          className="rounded-full bg-zinc-100 px-2 py-0.5 text-xs text-zinc-700 hover:bg-zinc-200 focus-visible:outline-2 focus-visible:outline-blue-500 dark:bg-zinc-800 dark:text-zinc-200 dark:hover:bg-zinc-700"
                        >
                          {product}
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
                <div className="mt-3">
                  <a
                    href={item.url}
                    target="_blank"
                    rel="noopener nofollow"
                    className="text-xs font-medium text-blue-700 hover:underline dark:text-blue-400"
                  >
                    {t("news.openOriginal")} →
                  </a>
                </div>
              </li>
              );
            })}
          </ul>
        </section>
      ))}

      <div className="mt-4 flex justify-center">
        {nextCursor ? (
          <button
            type="button"
            onClick={loadMore}
            disabled={loadingMore}
            className="rounded border border-zinc-300 px-4 py-2 text-sm font-medium hover:bg-zinc-50 disabled:opacity-50 dark:border-zinc-700 dark:hover:bg-zinc-800"
          >
            {loadingMore ? t("news.loadingMore") : t("news.loadMore")}
          </button>
        ) : (
          <p className="text-xs text-zinc-500">{t("news.endOfResults")}</p>
        )}
      </div>
    </div>
  );
}
