"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { toggleVote, type NewsItem, type VoteState } from "@/lib/api";
import type { BrowserIdentity } from "@/lib/localIdentity";

interface HelpfulButtonProps {
  item: NewsItem;
  identity: BrowserIdentity | null;
  state?: VoteState;
  onChange: (newsItemId: string, state: VoteState) => void;
}

function voteTier(count: number) {
  if (count >= 6) {
    return {
      labelKey: "tierHot",
      className:
        "border-orange-300 bg-orange-50 text-orange-700 hover:bg-orange-100 dark:border-orange-800 dark:bg-orange-950/30 dark:text-orange-300",
      badgeClassName: "bg-orange-600 text-white",
    } as const;
  }
  if (count >= 3) {
    return {
      labelKey: "tierWarm",
      className:
        "border-amber-300 bg-amber-50 text-amber-700 hover:bg-amber-100 dark:border-amber-800 dark:bg-amber-950/30 dark:text-amber-300",
      badgeClassName: "bg-amber-500 text-white",
    } as const;
  }
  if (count >= 1) {
    return {
      labelKey: "tierUseful",
      className:
        "border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-100 dark:border-emerald-900 dark:bg-emerald-950/30 dark:text-emerald-300",
      badgeClassName: "bg-emerald-600 text-white",
    } as const;
  }
  return {
    labelKey: null,
    className:
      "border-slate-200 bg-white text-slate-500 hover:border-emerald-200 hover:bg-emerald-50 hover:text-emerald-700 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-400 dark:hover:border-emerald-900 dark:hover:bg-emerald-950/30 dark:hover:text-emerald-300",
    badgeClassName: "",
  } as const;
}

export function HelpfulButton({ item, identity, state, onChange }: HelpfulButtonProps) {
  const t = useTranslations("votes");
  const [busy, setBusy] = useState(false);
  const count = state?.count ?? item.helpfulVotes ?? 0;
  const voted = state?.votedByMe ?? false;
  const tier = voteTier(count);

  async function handleClick() {
    if (!identity || busy) return;
    const previous = { count, votedByMe: voted };
    const optimistic = {
      count: voted ? Math.max(0, count - 1) : count + 1,
      votedByMe: !voted,
    };
    onChange(item.id, optimistic);
    setBusy(true);
    try {
      const result = await toggleVote({
        newsItemId: item.id,
        userId: identity.userId,
        userSecret: identity.userSecret,
      });
      onChange(item.id, { count: result.count, votedByMe: result.votedByMe });
    } catch {
      onChange(item.id, previous);
    } finally {
      setBusy(false);
    }
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={!identity || busy}
      aria-pressed={voted}
      className={
        "inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wide shadow-sm transition-colors disabled:opacity-50 " +
        tier.className +
        (voted ? " ring-1 ring-current/20" : "")
      }
      title={t("title")}
    >
      {tier.labelKey && (
        <span
          aria-hidden="true"
          className={`rounded-full px-1.5 py-0.5 text-[9px] font-bold ${tier.badgeClassName}`}
        >
          {t(tier.labelKey)}
        </span>
      )}
      <span>{t("helpful")}</span>
      <span className="tabular-nums">{count}</span>
    </button>
  );
}
