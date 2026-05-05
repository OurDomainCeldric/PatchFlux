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
        "inline-flex items-center gap-1.5 rounded-full border px-3.5 py-1.5 text-[11px] font-bold uppercase tracking-wide shadow-sm transition-all hover:-translate-y-0.5 disabled:translate-y-0 disabled:opacity-50 " +
        (voted
          ? "border-orange-300 bg-orange-100 text-orange-800 shadow-orange-100 hover:bg-orange-200 dark:border-orange-700 dark:bg-orange-950/50 dark:text-orange-200 dark:shadow-none"
          : "border-orange-200 bg-gradient-to-r from-orange-50 to-amber-50 text-orange-700 hover:border-orange-300 hover:from-orange-100 hover:to-amber-100 dark:border-orange-900/70 dark:from-orange-950/40 dark:to-amber-950/30 dark:text-orange-300")
      }
      title={t("title")}
    >
      <span aria-hidden="true" className="rounded-full bg-orange-600 px-1.5 py-0.5 text-[9px] text-white">
        HOT
      </span>
      <span>{t("helpful")}</span>
      <span className="tabular-nums">{count}</span>
    </button>
  );
}
