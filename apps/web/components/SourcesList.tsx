"use client";

import { useEffect, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { fetchSources, type SourceHealth } from "@/lib/api";

export function SourcesList() {
  const t = useTranslations();
  const locale = useLocale();
  const [sources, setSources] = useState<SourceHealth[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchSources()
      .then((response) => {
        if (!cancelled) setSources(response.sources);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const dateFormatter = new Intl.DateTimeFormat(locale, {
    dateStyle: "medium",
    timeStyle: "short",
  });

  return (
    <section>
      <h1 className="mb-2 text-lg font-semibold">{t("sources.heading")}</h1>
      <p className="mb-4 text-sm text-zinc-600 dark:text-zinc-400">
        {t("sources.description")}
      </p>
      {error && (
        <p className="text-sm text-red-700 dark:text-red-400">{t("news.loadError")}</p>
      )}
      {sources === null && !error && (
        <p className="text-sm text-zinc-500">{t("news.loading")}</p>
      )}
      {sources && (
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="text-left text-xs uppercase text-zinc-500">
              <th className="py-2">ID</th>
              <th className="py-2">{t("sources.status")}</th>
              <th className="py-2">{t("sources.lastFetch")}</th>
            </tr>
          </thead>
          <tbody>
            {sources.map((source) => (
              <tr key={source.sourceId} className="border-t border-zinc-200 dark:border-zinc-800">
                <td className="py-2 font-mono text-xs">{source.sourceId}</td>
                <td className="py-2">{source.lastStatus ?? "—"}</td>
                <td className="py-2 text-xs text-zinc-500">
                  {source.lastFetchAt
                    ? dateFormatter.format(new Date(source.lastFetchAt))
                    : t("sources.never")}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
