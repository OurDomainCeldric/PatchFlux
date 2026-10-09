"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { fetchRoadmap, type RoadmapItem } from "@/lib/api";

const PREFERENCE_KEY = "patchflux:roadmap:product";
const VISIT_KEY = "patchflux:roadmap:lastVisit";

export function RoadmapExplorer() {
  const t = useTranslations("roadmap");
  const locale = useLocale();
  const [items, setItems] = useState<RoadmapItem[] | null>(null);
  const [error, setError] = useState(false);
  const [product, setProduct] = useState("");
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const [lastVisit, setLastVisit] = useState<string | null>(null);
  const [changesOnly, setChangesOnly] = useState(false);
  const [limit, setLimit] = useState(30);

  useEffect(() => {
    let cancelled = false;
    try {
      setProduct(localStorage.getItem(PREFERENCE_KEY) ?? "");
      const previous = localStorage.getItem(VISIT_KEY);
      if (previous && Number.isFinite(Date.parse(previous))) setLastVisit(previous);
    } catch { /* Storage is optional. */ }
    fetchRoadmap().then((response) => {
      if (cancelled) return;
      setItems(response.items);
      try { localStorage.setItem(VISIT_KEY, new Date().toISOString()); } catch { /* optional */ }
    }).catch(() => { if (!cancelled) setError(true); });
    return () => { cancelled = true; };
  }, []);

  const products = Array.from(new Set((items ?? []).flatMap((item) => item.products))).sort();
  const filtered = (items ?? []).filter((item) =>
    (!product || item.products.includes(product)) &&
    (!status || item.status === status) &&
    (!changesOnly || (lastVisit !== null && Date.parse(item.changedAt) > Date.parse(lastVisit))) &&
    `${item.title} ${item.id}`.toLowerCase().includes(query.toLowerCase().trim()),
  );
  const dateFormatter = new Intl.DateTimeFormat(locale, { dateStyle: "medium" });
  const statusKey = (value: RoadmapItem["status"]) => ({
    "in development": "development", "rolling out": "rollout", launched: "launched", unknown: "unknown",
  })[value];
  const controlClass = "rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900";

  return (
    <div>
      <Link href={`/${locale}`} className="text-sm text-indigo-600 dark:text-indigo-400">{t("back")}</Link>
      <header className="mb-6 mt-5 border-l-4 border-teal-500 pl-4">
        <h1 className="text-2xl font-semibold tracking-tight">M365 Roadmap</h1>
        <p className="mt-2 max-w-2xl text-sm text-slate-500 dark:text-slate-400">{t("intro")}</p>
      </header>
      <div className="mb-5 flex flex-wrap gap-3 rounded-xl border border-slate-200 bg-slate-50 p-3 dark:border-slate-800 dark:bg-slate-900/50">
        <input aria-label={t("search")} placeholder={t("search")} value={query} onChange={(event) => { setQuery(event.target.value); setLimit(30); }} className={`${controlClass} min-w-0 flex-1`} />
        <select aria-label={t("product")} value={product} onChange={(event) => {
          setProduct(event.target.value); setLimit(30);
          try { localStorage.setItem(PREFERENCE_KEY, event.target.value); } catch { /* optional */ }
        }} className={controlClass}>
          <option value="">{t("allProducts")}</option>
          {products.map((value) => <option key={value} value={value}>{value}</option>)}
        </select>
        <select aria-label={t("status")} value={status} onChange={(event) => { setStatus(event.target.value); setLimit(30); }} className={controlClass}>
          <option value="">{t("allStatuses")}</option>
          {(["in development", "rolling out", "launched", "unknown"] as const).map((value) => <option key={value} value={value}>{t(statusKey(value))}</option>)}
        </select>
        {lastVisit && <label className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-300">
          <input type="checkbox" checked={changesOnly} onChange={(event) => { setChangesOnly(event.target.checked); setLimit(30); }} />{t("changesOnly")}
        </label>}
      </div>
      {error ? <p role="alert">{t("error")}</p> : items === null ? <p role="status">{t("loading")}</p> : <>
        <p aria-live="polite" className="mb-3 text-xs text-slate-500">{t("count", { count: filtered.length })}</p>
        {!filtered.length && <p className="rounded-lg border border-slate-200 p-6 text-sm dark:border-slate-800">{t("empty")}</p>}
        <ul className="divide-y divide-slate-100 overflow-hidden rounded-xl border border-slate-200 bg-white dark:divide-slate-800 dark:border-slate-800 dark:bg-slate-900">
          {filtered.slice(0, limit).map((item) => {
            const changed = lastVisit !== null && Date.parse(item.changedAt) > Date.parse(lastVisit);
            return <li key={item.id} className="px-4 py-4 sm:px-5">
              <div className="mb-1.5 flex flex-wrap items-center gap-2 text-[11px] text-slate-500">
                <span className="font-mono">#{item.id}</span>
                {item.products.map((value) => <span key={value}>{value}</span>)}
                <span className="rounded bg-teal-50 px-2 py-0.5 text-teal-800 dark:bg-teal-950 dark:text-teal-200">{t(statusKey(item.status))}</span>
                {changed && <span className="font-semibold text-indigo-600 dark:text-indigo-300">{t("changed")}</span>}
              </div>
              <a href={item.url} target="_blank" rel="noopener nofollow" className="text-sm font-medium leading-relaxed hover:text-indigo-600 focus-visible:outline-2 focus-visible:outline-indigo-500">{item.title}</a>
              <p className="mt-1.5 text-[11px] text-slate-500">Microsoft 365 Roadmap · {t("observed")} <time dateTime={item.changedAt}>{dateFormatter.format(new Date(item.changedAt))}</time></p>
            </li>;
          })}
        </ul>
        {filtered.length > limit && <button type="button" onClick={() => setLimit((value) => value + 30)} className={`${controlClass} mt-4`}>{t("more")}</button>}
      </>}
      <p className="mt-5 text-xs text-slate-500">{t("note")}</p>
    </div>
  );
}
