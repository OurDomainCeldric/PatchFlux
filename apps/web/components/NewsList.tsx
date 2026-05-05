"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { fetchCommentCounts, fetchNews, type NewsItem } from "@/lib/api";
import { CommentsPanel } from "@/components/CommentsPanel";
import {
  areAllNewsTopicsSelected,
  filtersToQuery,
  isDefaultTopicSet,
  readFiltersFromParams,
  type FilterState,
} from "@/components/FilterBar";
import { NewsListSkeleton } from "@/components/Skeleton";

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
  const isCommunity = searchParams?.get("tab") === "community";

  const filters = useMemo(
    () => readFiltersFromParams(searchParams ?? new URLSearchParams()),
    [searchParams],
  );

  const [items, setItems] = useState<NewsItem[] | null>(null);
  const [commentCounts, setCommentCounts] = useState<Record<string, number>>({});
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const requestIdRef = useRef(0);
  const hasNoSelectedTopics = filters.topics.size === 0;

  const fetchOptions = useMemo(() => {
    const opts: Parameters<typeof fetchNews>[0] = { limit: PAGE_SIZE };
    if (filters.source) opts.source = filters.source;
    if (filters.product) opts.product = filters.product;
    if (filters.lang === "de" || filters.lang === "en") opts.lang = filters.lang;
    if (filters.since) opts.since = filters.since;
    if (filters.q) opts.q = filters.q;
    if (filters.deduped) opts.deduped = true;
    // Community tab never passes hot=true (priority not relevant for forum posts)
    if (!isCommunity && filters.onlyHot) opts.hot = true;
    if (hasNoSelectedTopics) {
      opts.topics = [];
    } else if (isDefaultTopicSet(filters.topics)) {
      opts.excludeTopics = ["cve"];
    } else if (!areAllNewsTopicsSelected(filters.topics)) {
      opts.topics = Array.from(filters.topics);
    }
    // Always pass community flag so the API applies the right tier filter
    opts.community = isCommunity;
    return opts;
  }, [filters, hasNoSelectedTopics, isCommunity]);

  useEffect(() => {
    const requestId = ++requestIdRef.current;
    setItems(null);
    setNextCursor(null);
    setError(null);
    if (hasNoSelectedTopics) {
      setItems([]);
      return;
    }
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
  }, [fetchOptions, hasNoSelectedTopics]);

  useEffect(() => {
    if (!items || items.length === 0) {
      setCommentCounts({});
      return;
    }
    let cancelled = false;
    fetchCommentCounts(items.map((item) => item.id))
      .then((response) => {
        if (!cancelled) setCommentCounts(response.counts);
      })
      .catch(() => {
        if (!cancelled) setCommentCounts({});
      });
    return () => {
      cancelled = true;
    };
  }, [items]);

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
    return <NewsListSkeleton cards={5} />;
  }

  if (items.length === 0) {
    const summary = describeActiveFilters(filters, t);
    const hasActive = summary.length > 0;
    return (
      <div
        aria-live="polite"
        className="rounded-lg border border-zinc-200 bg-white p-6 text-center text-sm text-zinc-600 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-300"
      >
        <p className="font-medium">
          {hasActive ? t("news.emptyWithFilters") : t("news.empty")}
        </p>
        {hasActive && (
          <>
            <p className="mt-2 text-xs text-zinc-500">
              {t("news.activeFilters", { filters: summary.join(" · ") })}
            </p>
            <button
              type="button"
              onClick={() => {
                router.replace(pathname, { scroll: false });
              }}
              className="mt-3 rounded border border-zinc-300 px-3 py-1 text-xs hover:bg-zinc-50 focus-visible:outline-2 focus-visible:outline-blue-500 dark:border-zinc-700 dark:hover:bg-zinc-800"
            >
              {t("news.clearAll")}
            </button>
          </>
        )}
      </div>
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
          <h2 className="sticky top-16 z-10 -mx-4 mb-3 bg-[#f8fafc]/90 px-4 py-2 text-[11px] font-bold uppercase tracking-wider text-slate-500 backdrop-blur-md dark:bg-[#09090b]/90 dark:text-slate-400">
            {dateLabel}
          </h2>
          <ul className="space-y-4">
            {bucket.map((item) => {
              const hot = !isCommunity && item.priority >= 2;
              const notable = !isCommunity && item.priority === 1;
              return (
              <li
                key={item.id}
                className={
                  hot
                    ? "group relative rounded-xl border border-red-200/60 bg-gradient-to-br from-red-50/80 to-white p-5 shadow-sm transition-all duration-300 hover:-translate-y-1 hover:shadow-md dark:border-red-900/50 dark:from-red-950/20 dark:to-[#18181b] overflow-hidden"
                    : notable
                    ? "group relative rounded-xl border border-amber-200/60 bg-gradient-to-br from-amber-50/50 to-white p-5 shadow-sm transition-all duration-300 hover:-translate-y-1 hover:shadow-md dark:border-amber-900/40 dark:from-amber-950/20 dark:to-[#18181b] overflow-hidden"
                    : "group relative rounded-xl border border-slate-200/60 bg-white p-5 shadow-sm transition-all duration-300 hover:-translate-y-1 hover:shadow-md hover:border-indigo-200 dark:border-slate-800/60 dark:bg-[#18181b] dark:hover:border-indigo-900/50 overflow-hidden"
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
                      className="text-slate-900 dark:text-slate-100 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors focus-visible:underline focus-visible:outline-2 focus-visible:outline-indigo-500"
                      aria-label={t("news.openOriginalAria", { source: item.sourceName })}
                    >
                      {item.title}
                    </a>
                  </h3>
                  <button
                    type="button"
                    onClick={() => applyFilterChange({ source: item.sourceId })}
                    className="shrink-0 rounded-full border border-slate-200/80 bg-slate-50 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide text-slate-500 transition-colors hover:border-slate-300 hover:bg-slate-100 focus-visible:outline-2 focus-visible:outline-indigo-500 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-400 dark:hover:bg-slate-800"
                    title={item.sourceId}
                  >
                    {item.sourceName}
                  </button>
                </div>
                <p className="mt-2 flex flex-wrap items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
                  <span>
                    {t("news.publishedAt", {
                      date: timeFormatter.format(new Date(item.publishedAt)),
                    })}
                    {item.author ? ` · ${item.author}` : ""}
                  </span>
                  <span
                    className="inline-flex items-center rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-bold uppercase text-slate-500 dark:bg-slate-800 dark:text-slate-400"
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
                          className="rounded-full bg-slate-100/80 px-2.5 py-0.5 text-[11px] font-medium text-slate-600 transition-colors hover:bg-slate-200 focus-visible:outline-2 focus-visible:outline-indigo-500 dark:bg-slate-800/80 dark:text-slate-300 dark:hover:bg-slate-700"
                        >
                          {product}
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
                <div className="mt-4">
                  <a
                    href={item.url}
                    target="_blank"
                    rel="noopener nofollow"
                    className="inline-flex items-center gap-1 text-[11px] font-bold uppercase tracking-wide text-indigo-600 transition-colors hover:text-indigo-700 dark:text-indigo-400 dark:hover:text-indigo-300"
                  >
                    {t("news.openOriginal")}
                    <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M14 5l7 7m0 0l-7 7m7-7H3" />
                    </svg>
                  </a>
                </div>
                {hot && <div className="absolute left-0 top-0 h-full w-1 bg-red-500" />}
                {notable && <div className="absolute left-0 top-0 h-full w-1 bg-amber-400" />}
                <CommentsPanel
                  item={item}
                  initialCount={commentCounts[item.id]}
                  onCountChange={(newsItemId, count) =>
                    setCommentCounts((previous) => ({
                      ...previous,
                      [newsItemId]: count,
                    }))
                  }
                />
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

type Translator = ReturnType<typeof useTranslations>;

/**
 * Build a human-readable list of active filter labels, e.g.
 * ``["Source: msrc", "Topics: CVE, Security"]``. Returns an empty array
 * when the user has the default filter state (no overrides).
 */
function describeActiveFilters(state: FilterState, t: Translator): string[] {
  const out: string[] = [];
  if (state.source) out.push(t("filterLabels.source", { value: state.source }));
  if (state.product) out.push(t("filterLabels.product", { value: state.product }));
  if (state.lang) out.push(t("filterLabels.lang", { value: state.lang.toUpperCase() }));
  if (state.since) out.push(t("filterLabels.since", { value: state.since }));
  if (state.q) out.push(t("filterLabels.q", { value: state.q }));
  if (state.deduped) out.push(t("filterLabels.deduped"));
  if (state.onlyHot) out.push(t("filterLabels.onlyHot"));
  if (!isDefaultTopicSet(state.topics)) {
    const topicsArr = Array.from(state.topics);
    const labels = topicsArr.map((x) => t(`topics.${x as "cve"}`));
    out.push(
      t("filterLabels.topics", {
        value: labels.length ? labels.join(", ") : "—",
      }),
    );
  }
  return out;
}
