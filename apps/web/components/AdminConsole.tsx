"use client";

import { useEffect, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import {
  fetchHealth,
  fetchSources,
  triggerIngest,
  type HealthResponse,
  type SourceHealth,
  type IngestResponse,
} from "@/lib/api";

const STORAGE_KEY = "patchflux:functionKey";

function sourceStateBadgeClass(state: SourceHealth["state"]) {
  switch (state) {
    case "ok":
      return "inline-flex rounded bg-emerald-100 px-2 py-0.5 text-xs text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200";
    case "not_modified":
      return "inline-flex rounded bg-sky-100 px-2 py-0.5 text-xs text-sky-800 dark:bg-sky-900/40 dark:text-sky-200";
    case "disabled":
      return "inline-flex rounded bg-zinc-100 px-2 py-0.5 text-xs text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300";
    case "never":
    case "stale":
    case "timer_not_firing":
      return "inline-flex rounded bg-amber-100 px-2 py-0.5 text-xs text-amber-800 dark:bg-amber-900/40 dark:text-amber-200";
    case "error":
      return "inline-flex rounded bg-red-100 px-2 py-0.5 text-xs text-red-800 dark:bg-red-900/40 dark:text-red-200";
  }
}

export function AdminConsole() {
  const t = useTranslations();
  const locale = useLocale();
  const [key, setKey] = useState("");
  const [savedKey, setSavedKey] = useState<string | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [sources, setSources] = useState<SourceHealth[] | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<IngestResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        setSavedKey(stored);
        setKey(stored);
      }
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    void Promise.all([fetchHealth(), fetchSources(true)])
      .then(([h, s]) => {
        if (cancelled) return;
        setHealth(h);
        setSources(s.sources);
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

  function handleSaveKey() {
    try {
      localStorage.setItem(STORAGE_KEY, key);
      setSavedKey(key);
    } catch {
      /* ignore */
    }
  }

  function handleClearKey() {
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {
      /* ignore */
    }
    setKey("");
    setSavedKey(null);
  }

  async function runIngest(sourceId?: string) {
    if (!savedKey) {
      setError(t("admin.missingKey"));
      return;
    }
    setBusy(sourceId ?? "__all__");
    setError(null);
    try {
      const result = await triggerIngest(savedKey, sourceId);
      setLastResult(result);
      const [h, s] = await Promise.all([fetchHealth(), fetchSources(true)]);
      setHealth(h);
      setSources(s.sources);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t("admin.ingestError"));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-8">
      <section>
        <h1 className="mb-4 text-xl font-semibold">{t("admin.title")}</h1>
        <label className="block text-sm font-medium">{t("admin.keyLabel")}</label>
        <p className="mb-2 text-xs text-zinc-500">{t("admin.keyHint")}</p>
        <div className="flex flex-wrap gap-2">
          <input
            type="password"
            value={key}
            onChange={(e) => setKey(e.target.value)}
            className="min-w-[260px] flex-1 rounded border border-zinc-300 bg-white px-3 py-1.5 text-sm dark:border-zinc-700 dark:bg-zinc-900"
            autoComplete="off"
          />
          <button
            type="button"
            onClick={handleSaveKey}
            className="rounded bg-zinc-900 px-3 py-1.5 text-sm text-white hover:bg-zinc-700 dark:bg-zinc-100 dark:text-zinc-900"
          >
            {t("admin.keySave")}
          </button>
          <button
            type="button"
            onClick={handleClearKey}
            className="rounded border border-zinc-300 px-3 py-1.5 text-sm dark:border-zinc-700"
          >
            {t("admin.keyClear")}
          </button>
        </div>
      </section>

      <section>
        <h2 className="mb-2 text-lg font-semibold">{t("admin.health")}</h2>
        {health ? (
          <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
            <dt className="text-zinc-500">Status</dt>
            <dd>
              <span
                className={
                  health.status === "ok"
                    ? "inline-flex rounded bg-emerald-100 px-2 py-0.5 text-xs text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200"
                    : "inline-flex rounded bg-amber-100 px-2 py-0.5 text-xs text-amber-800 dark:bg-amber-900/40 dark:text-amber-200"
                }
              >
                {health.status === "ok" ? t("admin.healthOk") : t("admin.healthDegraded")}
              </span>
            </dd>
            <dt className="text-zinc-500">Storage</dt>
            <dd>{health.storage ? "ok" : "down"}</dd>
            <dt className="text-zinc-500">{t("admin.staleSources")}</dt>
            <dd className="font-mono text-xs">
              {health.sourcesStale.length === 0
                ? t("admin.none")
                : health.sourcesStale.join(", ")}
            </dd>
            <dt className="text-zinc-500">{t("admin.statusBreakdown")}</dt>
            <dd className="flex flex-wrap gap-2 text-xs">
              <span>{t("sources.states.ok")}: {health.sourceCounts.ok}</span>
              <span>{t("sources.states.not_modified")}: {health.sourceCounts.notModified}</span>
              <span>{t("sources.states.error")}: {health.sourceCounts.error}</span>
              <span>{t("sources.states.stale")}: {health.sourceCounts.stale}</span>
              <span>{t("sources.states.timer_not_firing")}: {health.sourceCounts.timerNotFiring}</span>
              <span>{t("sources.states.disabled")}: {health.sourceCounts.disabled}</span>
              <span>{t("sources.states.never")}: {health.sourceCounts.never}</span>
            </dd>
          </dl>
        ) : (
          <p className="text-sm text-zinc-500">{t("news.loading")}</p>
        )}
      </section>

      <section>
        <div className="mb-3 flex items-center gap-3">
          <h2 className="text-lg font-semibold">{t("sources.heading")}</h2>
          <button
            type="button"
            onClick={() => runIngest()}
            disabled={busy !== null || !savedKey}
            className="rounded bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-500 disabled:opacity-50"
          >
            {busy === "__all__" ? t("admin.triggering") : t("admin.triggerAll")}
          </button>
        </div>
        {error && (
          <p className="mb-3 text-sm text-red-700 dark:text-red-400">{error}</p>
        )}
        {sources && (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="text-left text-xs uppercase text-zinc-500">
                  <th className="py-2 pr-4">ID</th>
                  <th className="py-2 pr-4">{t("sources.state")}</th>
                  <th className="py-2 pr-4">{t("sources.status")}</th>
                  <th className="py-2 pr-4">{t("sources.itemsLastRun")}</th>
                  <th className="py-2 pr-4">{t("sources.lastAttempt")}</th>
                  <th className="py-2 pr-4">{t("sources.lastSuccess")}</th>
                  <th className="py-2 pr-4">{t("sources.lastFetch")}</th>
                  <th className="py-2 pr-4">{t("sources.error")}</th>
                  <th className="py-2"></th>
                </tr>
              </thead>
              <tbody>
                {sources.map((s) => (
                  <tr
                    key={s.sourceId}
                    className="border-t border-zinc-200 dark:border-zinc-800"
                  >
                    <td className="py-2 pr-4 font-mono text-xs">{s.sourceId}</td>
                    <td className="py-2 pr-4">
                      <span className={sourceStateBadgeClass(s.state)}>
                        {t(`sources.states.${s.state}`)}
                      </span>
                    </td>
                    <td className="py-2 pr-4 text-xs">{s.lastStatus ?? "—"}</td>
                    <td className="py-2 pr-4 tabular-nums text-xs">
                      {s.itemsLastRun ?? "—"}
                    </td>
                    <td className="py-2 pr-4 text-xs text-zinc-500">
                      {s.lastAttemptAt
                        ? dateFormatter.format(new Date(s.lastAttemptAt))
                        : t("sources.never")}
                    </td>
                    <td className="py-2 pr-4 text-xs text-zinc-500">
                      {s.lastSuccessAt
                        ? dateFormatter.format(new Date(s.lastSuccessAt))
                        : t("sources.never")}
                    </td>
                    <td className="py-2 pr-4 text-xs text-zinc-500">
                      {s.lastFetchAt
                        ? dateFormatter.format(new Date(s.lastFetchAt))
                        : t("sources.never")}
                    </td>
                    <td
                      className="py-2 pr-4 max-w-[16rem] truncate text-xs text-zinc-500"
                      title={s.lastError ?? ""}
                    >
                      {s.lastError ?? "—"}
                    </td>
                    <td className="py-2">
                      <button
                        type="button"
                        onClick={() => runIngest(s.sourceId)}
                        disabled={busy !== null || !savedKey || s.state === "disabled"}
                        className="rounded border border-zinc-300 px-2 py-1 text-xs hover:bg-zinc-100 disabled:opacity-50 dark:border-zinc-700 dark:hover:bg-zinc-800"
                      >
                        {busy === s.sourceId
                          ? t("admin.triggering")
                          : t("admin.triggerSingle")}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {lastResult && (
        <section>
          <h2 className="mb-2 text-lg font-semibold">{t("admin.lastResult")}</h2>
          <pre className="overflow-x-auto rounded bg-zinc-100 p-3 text-xs dark:bg-zinc-900">
            {JSON.stringify(lastResult, null, 2)}
          </pre>
        </section>
      )}
    </div>
  );
}
