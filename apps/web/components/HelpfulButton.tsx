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

export function HelpfulButton({ item, identity, state, onChange }: HelpfulButtonProps) {
  const t = useTranslations("votes");
  const [busy, setBusy] = useState(false);
  const count = state?.count ?? item.helpfulVotes ?? 0;
  const voted = state?.votedByMe ?? false;

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
        "inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide transition-colors disabled:opacity-50 " +
        (voted
          ? "border-emerald-300 bg-emerald-50 text-emerald-700 hover:bg-emerald-100 dark:border-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300"
          : "border-slate-200 bg-slate-50 text-slate-500 hover:border-emerald-300 hover:text-emerald-700 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-400")
      }
      title={t("title")}
    >
      <span aria-hidden="true">▲</span>
      <span>{t("helpful")}</span>
      <span className="tabular-nums">{count}</span>
    </button>
  );
}
