"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { fetchVisitCounts, trackVisit, type VisitCountsResponse } from "@/lib/api";

const STORAGE_PREFIX = "patchflux:visit-counted:";

export function VisitCounter() {
  const t = useTranslations();
  const [counts, setCounts] = useState<VisitCountsResponse | null>(null);

  useEffect(() => {
    let cancelled = false;
    const todayKey = new Date().toISOString().slice(0, 10);
    const storageKey = `${STORAGE_PREFIX}${todayKey}`;

    async function load() {
      try {
        const alreadyCounted = window.localStorage.getItem(storageKey) === "1";
        const data = alreadyCounted
          ? await fetchVisitCounts()
          : await trackVisit();
        if (!alreadyCounted) {
          window.localStorage.setItem(storageKey, "1");
        }
        if (!cancelled) {
          setCounts(data);
        }
      } catch {
        if (!cancelled) {
          setCounts(null);
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  if (!counts) {
    return null;
  }

  return (
    <p className="text-[10px] text-zinc-400 dark:text-zinc-500">
      {t("footer.visitCounter", {
        today: counts.today,
        allTime: counts.allTime,
      })}
    </p>
  );
}
