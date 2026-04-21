"use client";

import { useEffect, useMemo, useState, type ChangeEvent } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { fetchProducts, fetchSources, type ProductCount, type SourceHealth } from "@/lib/api";

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
  return sp;
}

interface FilterBarProps {
  pathname: string;
}

export function FilterBar({ pathname }: FilterBarProps) {
  const t = useTranslations("filters");
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
    });
  };

  return (
    <section
      aria-label={t("heading")}
      className="mb-6 rounded-lg border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900"
    >
      <div className="grid grid-cols-1 gap-3 md:grid-cols-3 lg:grid-cols-5">
        <label className="flex flex-col gap-1 text-xs">
          <span className="text-zinc-600 dark:text-zinc-300">{t("source")}</span>
          <select
            value={current.source}
            onChange={updateField("source")}
            className="rounded border border-zinc-300 bg-white px-2 py-1 text-sm dark:border-zinc-700 dark:bg-zinc-950"
          >
            <option value="">{t("allSources")}</option>
            {sources.map((s) => (
              <option key={s.sourceId} value={s.sourceId}>
                {s.sourceId}
              </option>
            ))}
          </select>
        </label>

        <label className="flex flex-col gap-1 text-xs">
          <span className="text-zinc-600 dark:text-zinc-300">{t("product")}</span>
          <select
            value={current.product}
            onChange={updateField("product")}
            className="rounded border border-zinc-300 bg-white px-2 py-1 text-sm dark:border-zinc-700 dark:bg-zinc-950"
          >
            <option value="">{t("allProducts")}</option>
            {products.map((p) => (
              <option key={p.id} value={p.id}>
                {p.id} ({p.count})
              </option>
            ))}
          </select>
        </label>

        <label className="flex flex-col gap-1 text-xs">
          <span className="text-zinc-600 dark:text-zinc-300">{t("language")}</span>
          <select
            value={current.lang}
            onChange={updateField("lang")}
            className="rounded border border-zinc-300 bg-white px-2 py-1 text-sm dark:border-zinc-700 dark:bg-zinc-950"
          >
            <option value="">{t("allLanguages")}</option>
            <option value="de">DE</option>
            <option value="en">EN</option>
          </select>
        </label>

        <label className="flex flex-col gap-1 text-xs">
          <span className="text-zinc-600 dark:text-zinc-300">{t("since")}</span>
          <select
            value={current.since}
            onChange={updateField("since")}
            className="rounded border border-zinc-300 bg-white px-2 py-1 text-sm dark:border-zinc-700 dark:bg-zinc-950"
          >
            {SINCE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {t(opt.labelKey)}
              </option>
            ))}
          </select>
        </label>

        <label className="flex flex-col gap-1 text-xs">
          <span className="text-zinc-600 dark:text-zinc-300">{t("search")}</span>
          <input
            type="search"
            value={draftQ}
            onChange={(event) => setDraftQ(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") submitSearch();
            }}
            onBlur={submitSearch}
            placeholder={t("searchPlaceholder")}
            className="rounded border border-zinc-300 bg-white px-2 py-1 text-sm dark:border-zinc-700 dark:bg-zinc-950"
          />
        </label>
      </div>

      <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-4">
          <label className="flex items-center gap-2 text-xs text-zinc-700 dark:text-zinc-300">
            <input
              type="checkbox"
              checked={current.onlyHot}
              onChange={updateField("onlyHot")}
              className="h-3 w-3"
            />
            <span>{t("onlyHot")}</span>
          </label>
          <label className="flex items-center gap-2 text-xs text-zinc-700 dark:text-zinc-300">
            <input
              type="checkbox"
              checked={current.deduped}
              onChange={updateField("deduped")}
              className="h-3 w-3"
            />
            <span>{t("deduped")}</span>
          </label>
        </div>
        <button
          type="button"
          onClick={reset}
          className="rounded border border-zinc-300 px-3 py-1 text-xs hover:bg-zinc-50 dark:border-zinc-700 dark:hover:bg-zinc-800"
        >
          {t("reset")}
        </button>
      </div>
    </section>
  );
}
