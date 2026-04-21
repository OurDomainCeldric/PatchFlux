"use client";

import { useEffect, useMemo, useState, type ChangeEvent } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { fetchProducts, fetchSources, type ProductCount, type SourceHealth } from "@/lib/api";

/** Topic ids known to the backend (see apps/functions/topics.py). */
export const TOPICS = [
  "new-features",
  "changes",
  "cve",
  "security",
  "compliance",
  "outage",
] as const;
export type Topic = (typeof TOPICS)[number];

const SINCE_OPTIONS: { value: string; labelKey: string }[] = [
  { value: "", labelKey: "sinceAll" },
  { value: "24h", labelKey: "since24h" },
  { value: "7d", labelKey: "since7d" },
  { value: "30d", labelKey: "since30d" },
];

export interface FilterState {
  source: string;
  product: string;
  lang: string;
  since: string;
  q: string;
  deduped: boolean;
  onlyHot: boolean;
  /** Empty set means "all topics". A non-empty set means "only those". */
  topics: Set<Topic>;
}

function parseTopics(raw: string | null): Set<Topic> {
  if (!raw) return new Set();
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
  if (state.topics.size > 0) {
    // Preserve canonical order.
    sp.set(
      "topics",
      TOPICS.filter((t) => state.topics.has(t)).join(","),
    );
  }
  return sp;
}

function advancedIsActive(state: FilterState): boolean {
  return Boolean(
    state.source || state.product || state.lang || state.since || state.deduped,
  );
}

interface FilterBarProps {
  pathname: string;
}

export function FilterBar({ pathname }: FilterBarProps) {
  const t = useTranslations();
  const router = useRouter();
  const searchParams = useSearchParams();

  const current = useMemo(
    () => readFiltersFromParams(searchParams ?? new URLSearchParams()),
    [searchParams],
  );

  const [draftQ, setDraftQ] = useState(current.q);
  const [sources, setSources] = useState<SourceHealth[]>([]);
  const [products, setProducts] = useState<ProductCount[]>([]);

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
    return () => {
      cancelled = true;
    };
  }, []);

  const navigate = (next: FilterState) => {
    const qs = filtersToQuery(next).toString();
    router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
  };

  const toggleTopic = (topic: Topic) => {
    const next = new Set(current.topics);
    if (next.has(topic)) next.delete(topic);
    else next.add(topic);
    navigate({ ...current, topics: next });
  };

  const setAllTopics = (allOn: boolean) => {
    const next: Set<Topic> = allOn ? new Set() : new Set(TOPICS);
    // "all on" is represented as the empty set (no filter at all).
    navigate({ ...current, topics: allOn ? new Set() : next });
  };

  const updateField =
    <K extends keyof FilterState>(key: K) =>
    (event: ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
      const raw =
        event.target instanceof HTMLInputElement && event.target.type === "checkbox"
          ? event.target.checked
          : event.target.value;
      navigate({ ...current, [key]: raw } as FilterState);
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
      topics: new Set<Topic>(),
    });
  };

  // "All topics" is selected when the user has not picked any (empty set).
  const allTopicsOn = current.topics.size === 0;
  const advancedActive = advancedIsActive(current);

  return (
    <section
      aria-label={t("filters.heading")}
      className="mb-6 rounded-lg border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900"
    >
      {/* Topic chips --------------------------------------------------- */}
      <div className="mb-3">
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-zinc-600 dark:text-zinc-300">
            {t("filters.topics")}
          </h2>
          <button
            type="button"
            onClick={() => setAllTopics(true)}
            disabled={allTopicsOn}
            className="text-xs text-blue-700 hover:underline disabled:text-zinc-400 disabled:no-underline dark:text-blue-400"
          >
            {t("filters.allTopics")}
          </button>
        </div>
        <ul role="group" aria-label={t("filters.topics")} className="flex flex-wrap gap-2">
          {TOPICS.map((topic) => {
            const active = allTopicsOn || current.topics.has(topic);
            return (
              <li key={topic}>
                <button
                  type="button"
                  aria-pressed={active}
                  onClick={() => toggleTopic(topic)}
                  className={
                    active
                      ? "rounded-full border border-blue-600 bg-blue-600 px-3 py-1 text-xs font-medium text-white shadow-sm transition hover:bg-blue-500 focus-visible:outline-2 focus-visible:outline-blue-700"
                      : "rounded-full border border-zinc-300 bg-white px-3 py-1 text-xs font-medium text-zinc-600 transition hover:bg-zinc-50 focus-visible:outline-2 focus-visible:outline-blue-500 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-800"
                  }
                >
                  {t(`topics.${topic}`)}
                </button>
              </li>
            );
          })}
        </ul>
      </div>

      {/* Search + quick switches -------------------------------------- */}
      <div className="flex flex-wrap items-center gap-3">
        <label className="flex min-w-[240px] flex-1 items-center gap-2 rounded border border-zinc-300 bg-white px-3 py-1.5 text-sm focus-within:outline-2 focus-within:outline-blue-500 dark:border-zinc-700 dark:bg-zinc-950">
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

        <label className="flex items-center gap-2 text-xs text-zinc-700 dark:text-zinc-300">
          <input
            type="checkbox"
            checked={current.onlyHot}
            onChange={updateField("onlyHot")}
            className="h-3 w-3"
          />
          <span>{t("filters.onlyHot")}</span>
        </label>

        <button
          type="button"
          onClick={reset}
          className="rounded border border-zinc-300 px-3 py-1 text-xs hover:bg-zinc-50 dark:border-zinc-700 dark:hover:bg-zinc-800"
        >
          {t("filters.reset")}
        </button>
      </div>

      {/* Advanced filters --------------------------------------------- */}
      <details
        className="mt-4 rounded border border-zinc-200 dark:border-zinc-800"
        open={advancedActive}
      >
        <summary className="flex cursor-pointer list-none items-center justify-between gap-2 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-zinc-600 hover:bg-zinc-50 dark:text-zinc-300 dark:hover:bg-zinc-800">
          <span>{t("filters.advanced")}</span>
          {advancedActive && (
            <span className="rounded bg-blue-100 px-2 py-0.5 text-[10px] font-bold text-blue-800 dark:bg-blue-900/50 dark:text-blue-200">
              {t("filters.active")}
            </span>
          )}
        </summary>
        <div className="grid grid-cols-1 gap-3 border-t border-zinc-200 p-3 md:grid-cols-2 lg:grid-cols-4 dark:border-zinc-800">
          <label className="flex flex-col gap-1 text-xs">
            <span className="text-zinc-600 dark:text-zinc-300">{t("filters.source")}</span>
            <select
              value={current.source}
              onChange={updateField("source")}
              className="rounded border border-zinc-300 bg-white px-2 py-1 text-sm dark:border-zinc-700 dark:bg-zinc-950"
            >
              <option value="">{t("filters.allSources")}</option>
              {sources.map((s) => (
                <option key={s.sourceId} value={s.sourceId}>
                  {s.sourceId}
                </option>
              ))}
            </select>
          </label>

          <label className="flex flex-col gap-1 text-xs">
            <span className="text-zinc-600 dark:text-zinc-300">{t("filters.product")}</span>
            <select
              value={current.product}
              onChange={updateField("product")}
              className="rounded border border-zinc-300 bg-white px-2 py-1 text-sm dark:border-zinc-700 dark:bg-zinc-950"
            >
              <option value="">{t("filters.allProducts")}</option>
              {products.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.id} ({p.count})
                </option>
              ))}
            </select>
          </label>

          <label className="flex flex-col gap-1 text-xs">
            <span className="text-zinc-600 dark:text-zinc-300">
              {t("filters.language")}
            </span>
            <select
              value={current.lang}
              onChange={updateField("lang")}
              className="rounded border border-zinc-300 bg-white px-2 py-1 text-sm dark:border-zinc-700 dark:bg-zinc-950"
            >
              <option value="">{t("filters.allLanguages")}</option>
              <option value="de">DE</option>
              <option value="en">EN</option>
            </select>
          </label>

          <label className="flex flex-col gap-1 text-xs">
            <span className="text-zinc-600 dark:text-zinc-300">{t("filters.since")}</span>
            <select
              value={current.since}
              onChange={updateField("since")}
              className="rounded border border-zinc-300 bg-white px-2 py-1 text-sm dark:border-zinc-700 dark:bg-zinc-950"
            >
              {SINCE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {t(`filters.${opt.labelKey}`)}
                </option>
              ))}
            </select>
          </label>

          <label className="col-span-full flex items-center gap-2 text-xs text-zinc-700 dark:text-zinc-300">
            <input
              type="checkbox"
              checked={current.deduped}
              onChange={updateField("deduped")}
              className="h-3 w-3"
            />
            <span>{t("filters.deduped")}</span>
          </label>
        </div>
      </details>
    </section>
  );
}
