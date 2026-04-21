"use client";

import { useEffect, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { fetchNews, type NewsItem } from "@/lib/api";

export function NewsList() {
  const t = useTranslations();
  const locale = useLocale();
  const [items, setItems] = useState<NewsItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setItems(null);
    setError(null);
    fetchNews({ limit: 50 })
      .then((response) => {
        if (!cancelled) setItems(response.items);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      });
    return () => {
      cancelled = true;
    };
  }, [reloadKey]);

  if (error) {
    return (
      <div className="rounded border border-red-300 bg-red-50 p-4 text-sm text-red-900 dark:border-red-800 dark:bg-red-950/40 dark:text-red-200">
        <p className="font-medium">{t("news.loadError")}</p>
        <button
          type="button"
          onClick={() => setReloadKey((n) => n + 1)}
          className="mt-2 rounded border border-red-300 px-3 py-1 text-xs hover:bg-red-100 dark:border-red-800 dark:hover:bg-red-900/40"
        >
          {t("news.retry")}
        </button>
      </div>
    );
  }

  if (items === null) {
    return <p className="text-sm text-zinc-500">{t("news.loading")}</p>;
  }

  if (items.length === 0) {
    return <p className="text-sm text-zinc-500">{t("news.empty")}</p>;
  }

  const dateFormatter = new Intl.DateTimeFormat(locale, {
    dateStyle: "medium",
    timeStyle: "short",
  });

  return (
    <ul className="space-y-4">
      {items.map((item) => (
        <li
          key={item.id}
          className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900"
        >
          <div className="flex items-start justify-between gap-4">
            <h2 className="text-base font-medium leading-snug">
              <a
                href={item.url}
                target="_blank"
                rel="noopener nofollow"
                className="hover:underline"
                aria-label={t("news.openOriginalAria", { source: item.sourceName })}
              >
                {item.title}
              </a>
            </h2>
            <span className="shrink-0 rounded border border-zinc-300 px-2 py-0.5 text-xs uppercase text-zinc-600 dark:border-zinc-700 dark:text-zinc-300">
              {item.sourceName}
            </span>
          </div>
          <p className="mt-1 text-xs text-zinc-500">
            {t("news.publishedAt", { date: dateFormatter.format(new Date(item.publishedAt)) })}
            {item.author ? ` · ${item.author}` : ""}
          </p>
          {item.products.length > 0 && (
            <ul className="mt-2 flex flex-wrap gap-1">
              {item.products.map((product) => (
                <li
                  key={product}
                  className="rounded-full bg-zinc-100 px-2 py-0.5 text-xs text-zinc-700 dark:bg-zinc-800 dark:text-zinc-200"
                >
                  {product}
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
      ))}
    </ul>
  );
}
