"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { fetchProducts, fetchSources, fetchTopics, type ProductCount, type SourceHealth } from "@/lib/api";

/** Topic ids known to the backend (see apps/functions/topics.py). */
export const TOPICS = [
  "new-features",
  "changes",
  "cve",
  "security",
  "compliance",
  "outage",
  "community",
] as const;
export type Topic = (typeof TOPICS)[number];

/** Default topic selection for the main feed: all editorial topics, no community-only chip. */
export const DEFAULT_TOPICS: readonly Topic[] = TOPICS.filter(
  (t) => t !== "community",
);
const NEWS_TOPICS: readonly Topic[] = DEFAULT_TOPICS;

export function isDefaultTopicSet(s: Set<Topic>): boolean {
  if (s.size !== DEFAULT_TOPICS.length) return false;
  return DEFAULT_TOPICS.every((t) => s.has(t));
}

const SINCE_OPTIONS: { value: string; labelKey: string }[] = [
  { value: "24h", labelKey: "since24h" },
  { value: "7d", labelKey: "since7d" },
  { value: "30d", labelKey: "since30d" },
];

const LANG_OPTIONS: { value: string; label: string }[] = [
  { value: "de", label: "DE" },
  { value: "en", label: "EN" },
];

export interface FilterState {
  source: string;
  product: string;
  lang: string;
  since: string;
  q: string;
  deduped: boolean;
  onlyHot: boolean;
  /** Empty set means "no matches". Omitted URL param means the DEFAULT set. */
  topics: Set<Topic>;
}

function parseTopics(raw: string | null): Set<Topic> {
  // Absent param means the DEFAULT selection.
  if (raw === null) return new Set<Topic>(DEFAULT_TOPICS);
  const known = new Set<Topic>(TOPICS);
  return new Set(
    raw
      .split(",")
      .map((t) => t.trim().toLowerCase())
      .filter((t): t is Topic => known.has(t as Topic)),
  );
}

export function readFiltersFromParams(params: URLSearchParams): FilterState {
  return {
    source: params.get("source") ?? "",
    product: params.get("product") ?? "",
    lang: params.get("lang") ?? "",
    since: params.get("since") ?? "",
    q: params.get("q") ?? "",
    deduped: params.get("deduped") === "1",
    onlyHot: params.get("hot") === "1",
    topics: parseTopics(params.get("topics")),
  };
}

export function filtersToQuery(state: FilterState): URLSearchParams {
  const sp = new URLSearchParams();
  if (state.source) sp.set("source", state.source);
  if (state.product) sp.set("product", state.product);
  if (state.lang) sp.set("lang", state.lang);
  if (state.since) sp.set("since", state.since);
  if (state.q) sp.set("q", state.q);
  if (state.deduped) sp.set("deduped", "1");
  if (state.onlyHot) sp.set("hot", "1");
  // Serialize whenever the selection differs from the DEFAULT set
  // (empty, partial, or full including CVE).
  if (!isDefaultTopicSet(state.topics)) {
    sp.set(
      "topics",
      TOPICS.filter((t) => state.topics.has(t)).join(","),
    );
  }
  return sp;
}

function advancedActiveCount(state: FilterState): number {
  let n = 0;
  if (state.source) n += 1;
  if (state.product) n += 1;
  if (state.lang) n += 1;
  if (state.since) n += 1;
  if (state.deduped) n += 1;
  if (!isDefaultTopicSet(state.topics)) n += 1;
  return n;
}

interface FilterBarProps {
  pathname: string;
}

/** Pill-style toggle button with aria-pressed. */
function TogglePill({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={
        active
          ? "rounded-full border border-blue-600 bg-blue-600 px-3 py-1 text-xs font-medium text-white shadow-sm transition hover:bg-blue-500 focus-visible:outline-2 focus-visible:outline-blue-700"
          : "rounded-full border border-zinc-300 bg-white px-3 py-1 text-xs font-medium text-zinc-600 transition hover:bg-zinc-50 focus-visible:outline-2 focus-visible:outline-blue-500 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-800"
      }
    >
      {children}
    </button>
  );
}

export function FilterBar({ pathname }: FilterBarProps) {
  const t = useTranslations();
  const router = useRouter();
  const searchParams = useSearchParams();

  const isCommunity = searchParams?.get("tab") === "community";

  const current = useMemo(
    () => readFiltersFromParams(searchParams ?? new URLSearchParams()),
    [searchParams],
  );

  const [draftQ, setDraftQ] = useState(current.q);
  const [sources, setSources] = useState<SourceHealth[]>([]);
  const [products, setProducts] = useState<ProductCount[]>([]);
  const [topicCounts, setTopicCounts] = useState<Record<string, number>>({});
  const [advancedOpen, setAdvancedOpen] = useState(false);

  const advancedRef = useRef<HTMLDivElement | null>(null);

  const filteredSources = useMemo(() => {
    return sources.filter((s) => {
      const isReddit = s.sourceId.startsWith("reddit-");
      return isCommunity ? isReddit : !isReddit;
    });
  }, [sources, isCommunity]);

  useEffect(() => {
    setDraftQ(current.q);
  }, [current.q]);

  useEffect(() => {
    let cancelled = false;
    fetchSources()
      .then((r) => {
        if (!cancelled) setSources(r.sources);
      })
      .catch(() => {});
    fetchProducts(3)
      .then((r) => {
        if (!cancelled) setProducts(r.products);
      })
      .catch(() => {});
    fetchTopics(14)
      .then((r) => {
        if (cancelled) return;
        const map: Record<string, number> = {};
        for (const t of r.topics) map[t.id] = t.count;
        setTopicCounts(map);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  // Close dropdown on outside click / Escape.
  useEffect(() => {
    if (!advancedOpen) return;
    const onDown = (event: MouseEvent) => {
      if (!advancedRef.current) return;
      if (!advancedRef.current.contains(event.target as Node)) {
        setAdvancedOpen(false);
      }
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setAdvancedOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [advancedOpen]);

  const navigate = (next: FilterState) => {
    const qs = filtersToQuery(next);
    const tab = searchParams?.get("tab");
    if (tab) {
      qs.set("tab", tab);
    }
    const qsString = qs.toString();
    router.replace(qsString ? `${pathname}?${qsString}` : pathname, { scroll: false });
  };

  const toggleTopic = (topic: Topic) => {
    const next = new Set(current.topics);
    if (next.has(topic)) next.delete(topic);
    else next.add(topic);
    navigate({ ...current, topics: next });
  };

  const setAllTopics = () => {
    navigate({ ...current, topics: new Set<Topic>(NEWS_TOPICS) });
  };

  /** Toggle a single-select string field: clicking the active value clears it. */
  const toggleSingle = <K extends "source" | "product" | "lang" | "since">(
    key: K,
    value: string,
  ) => {
    const nextValue = current[key] === value ? "" : value;
    navigate({ ...current, [key]: nextValue } as FilterState);
  };

  const toggleBool = <K extends "deduped" | "onlyHot">(key: K) => {
    navigate({ ...current, [key]: !current[key] } as FilterState);
  };

  const submitSearch = () => {
    navigate({ ...current, q: draftQ.trim() });
  };

  const reset = () => {
    setDraftQ("");
    navigate({
      source: "",
      product: "",
      lang: "",
      since: "",
      q: "",
      deduped: false,
      onlyHot: false,
      // Reset goes back to the default topic selection.
      topics: new Set<Topic>(DEFAULT_TOPICS),
    });
  };

  const allTopicsOn = current.topics.size === NEWS_TOPICS.length;
  const advancedCount = advancedActiveCount(current);

  return (
    <section
      aria-label={t("filters.heading")}
      className="mb-4 sm:mb-6 rounded-lg border border-zinc-200 bg-white p-3 sm:p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900"
    >
      <div className="flex flex-wrap items-center gap-3">
        <label className="flex min-w-[240px] flex-1 items-center gap-2 rounded border border-zinc-300 bg-white px-2.5 py-1 sm:px-3 sm:py-1.5 text-sm focus-within:outline-2 focus-within:outline-blue-500 dark:border-zinc-700 dark:bg-zinc-950">
          <span aria-hidden className="text-zinc-400">
            ⌕
          </span>
          <span className="sr-only">{t("filters.search")}</span>
          <input
            type="search"
            value={draftQ}
            onChange={(event) => setDraftQ(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") submitSearch();
            }}
            onBlur={submitSearch}
            placeholder={t("filters.searchPlaceholder")}
            className="flex-1 bg-transparent outline-none placeholder:text-zinc-400"
          />
        </label>

        {!isCommunity && (
          <button
            type="button"
            aria-pressed={current.onlyHot}
            onClick={() => toggleBool("onlyHot")}
            className={
              current.onlyHot
                ? "rounded-full border border-red-600 bg-red-600 px-3 py-1 text-xs font-medium text-white shadow-sm hover:bg-red-500 focus-visible:outline-2 focus-visible:outline-red-700"
                : "rounded-full border border-zinc-300 bg-white px-3 py-1 text-xs font-medium text-zinc-600 hover:bg-zinc-50 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-800"
            }
          >
            {t("filters.onlyHot")}
          </button>
        )}

        {/* Advanced-filters icon toggle (dropdown) ------------------- */}
        <div className="relative" ref={advancedRef}>
          <button
            type="button"
            aria-expanded={advancedOpen}
            aria-haspopup="dialog"
            aria-controls="advanced-filters-panel"
            aria-label={t("filters.advanced")}
            title={t("filters.advanced")}
            onClick={() => setAdvancedOpen((v) => !v)}
            className={
              "relative inline-flex h-8 w-8 items-center justify-center rounded border hover:bg-zinc-50 focus-visible:outline-2 focus-visible:outline-blue-500 dark:hover:bg-zinc-800 " +
              (advancedCount > 0
                ? "border-blue-600 text-blue-700 dark:border-blue-500 dark:text-blue-300"
                : "border-zinc-300 text-zinc-700 dark:border-zinc-700 dark:text-zinc-300")
            }
          >
            <svg
              viewBox="0 0 20 20"
              fill="currentColor"
              aria-hidden="true"
              className="h-4 w-4"
            >
              <path d="M3 4.5A1.5 1.5 0 0 1 4.5 3h11a1.5 1.5 0 0 1 1.2 2.4l-4.7 6.27V16a1 1 0 0 1-.55.9l-2 1A1 1 0 0 1 8 17v-5.33L3.3 5.4A1.5 1.5 0 0 1 3 4.5Z" />
            </svg>
            {advancedCount > 0 && (
              <span
                aria-hidden
                className="absolute -right-1 -top-1 flex h-4 min-w-[1rem] items-center justify-center rounded-full bg-blue-600 px-1 text-[10px] font-bold text-white"
              >
                {advancedCount}
              </span>
            )}
            <span className="sr-only">
              {t("filters.advanced")}
              {advancedCount > 0 ? ` (${t("filters.active")})` : ""}
            </span>
          </button>

          {advancedOpen && (
            <div
              id="advanced-filters-panel"
              role="dialog"
              aria-modal="false"
              aria-labelledby="advanced-filters-heading"
              className="absolute right-0 top-full z-20 mt-2 w-[min(92vw,22rem)] rounded-lg border border-zinc-200 bg-white p-3 shadow-lg dark:border-zinc-800 dark:bg-zinc-900"
            >
              <div className="mb-3 flex items-center justify-between">
                <span
                  id="advanced-filters-heading"
                  className="text-xs font-semibold uppercase tracking-wide text-zinc-600 dark:text-zinc-300"
                >
                  {t("filters.advanced")}
                </span>
                {advancedCount > 0 && (
                  <span className="rounded bg-blue-100 px-2 py-0.5 text-[10px] font-bold text-blue-800 dark:bg-blue-900/50 dark:text-blue-200">
                    {t("filters.active")}
                  </span>
                )}
              </div>

              <div className="space-y-3">
                <fieldset>
                  <div className="flex items-center justify-between mb-1">
                    <legend className="text-[11px] font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
                      {t("filters.topics")}
                    </legend>
                    <button
                      type="button"
                      onClick={setAllTopics}
                      disabled={allTopicsOn}
                      className="text-[10px] text-blue-700 hover:underline disabled:text-zinc-400 disabled:no-underline dark:text-blue-400"
                    >
                      {t("filters.allTopics")}
                    </button>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {NEWS_TOPICS.map((topic) => {
                      const active = current.topics.has(topic);
                      const count = topicCounts[topic];
                      return (
                        <TogglePill key={topic} active={active} onClick={() => toggleTopic(topic)}>
                          {t(`topics.${topic}`)}
                          {typeof count === "number" && count > 0 && (
                            <span
                              aria-hidden="true"
                              className={
                                active
                                  ? "ml-1.5 rounded bg-white/20 px-1 text-[10px] font-semibold"
                                  : "ml-1.5 rounded bg-zinc-100 px-1 text-[10px] font-semibold text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400"
                              }
                            >
                              {count}
                            </span>
                          )}
                        </TogglePill>
                      );
                    })}
                  </div>
                </fieldset>

                <fieldset>
                  <legend className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
                    {t("filters.source")}
                  </legend>
                  <div className="flex flex-wrap gap-1.5">
                    {filteredSources.length === 0 && (
                      <span className="text-xs text-zinc-400">—</span>
                    )}
                    {filteredSources.map((s) => (
                      <TogglePill
                        key={s.sourceId}
                        active={current.source === s.sourceId}
                        onClick={() => toggleSingle("source", s.sourceId)}
                      >
                        {s.sourceId}
                      </TogglePill>
                    ))}
                  </div>
                </fieldset>

                {products.length > 0 && (
                  <fieldset>
                    <legend className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
                      {t("filters.product")}
                    </legend>
                    <div className="flex flex-wrap gap-1.5">
                      {products.map((p) => (
                        <TogglePill
                          key={p.id}
                          active={current.product === p.id}
                          onClick={() => toggleSingle("product", p.id)}
                        >
                          {p.id} ({p.count})
                        </TogglePill>
                      ))}
                    </div>
                  </fieldset>
                )}

                <fieldset>
                  <legend className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
                    {t("filters.language")}
                  </legend>
                  <div className="flex flex-wrap gap-1.5">
                    {LANG_OPTIONS.map((opt) => (
                      <TogglePill
                        key={opt.value}
                        active={current.lang === opt.value}
                        onClick={() => toggleSingle("lang", opt.value)}
                      >
                        {opt.label}
                      </TogglePill>
                    ))}
                  </div>
                </fieldset>

                <fieldset>
                  <legend className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
                    {t("filters.since")}
                  </legend>
                  <div className="flex flex-wrap gap-1.5">
                    {SINCE_OPTIONS.map((opt) => (
                      <TogglePill
                        key={opt.value}
                        active={current.since === opt.value}
                        onClick={() => toggleSingle("since", opt.value)}
                      >
                        {t(`filters.${opt.labelKey}`)}
                      </TogglePill>
                    ))}
                  </div>
                </fieldset>

                <fieldset>
                  <div className="flex flex-wrap gap-1.5">
                    <TogglePill
                      active={current.deduped}
                      onClick={() => toggleBool("deduped")}
                    >
                      {t("filters.deduped")}
                    </TogglePill>
                  </div>
                </fieldset>
              </div>

              <div className="mt-3 flex items-center justify-end gap-2 border-t border-zinc-200 pt-3 dark:border-zinc-800">
                <button
                  type="button"
                  onClick={reset}
                  className="rounded border border-zinc-300 px-3 py-1 text-xs hover:bg-zinc-50 dark:border-zinc-700 dark:hover:bg-zinc-800"
                >
                  {t("filters.reset")}
                </button>
                <button
                  type="button"
                  onClick={() => setAdvancedOpen(false)}
                  className="rounded border border-blue-600 bg-blue-600 px-3 py-1 text-xs font-medium text-white hover:bg-blue-500"
                >
                  {t("filters.close")}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
