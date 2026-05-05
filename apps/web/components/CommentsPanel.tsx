"use client";

import type { FormEvent } from "react";
import { useEffect, useMemo, useState } from "react";
import {
  createComment,
  fetchComments,
  type CommentItem,
  type NewsItem,
} from "@/lib/api";
import { useLocale, useTranslations } from "next-intl";

const STORAGE_KEY = "patchflux:commentIdentity";

interface CommentIdentity {
  userId: string;
  userSecret: string;
  displayName: string;
}

interface CommentsPanelProps {
  item: NewsItem;
}

function randomToken() {
  const browserCrypto = globalThis.crypto;
  if (browserCrypto?.randomUUID) {
    return browserCrypto.randomUUID();
  }
  const values = new Uint32Array(4);
  browserCrypto?.getRandomValues(values);
  return Array.from(values, (value) => value.toString(16).padStart(8, "0")).join("-");
}

function readIdentity(): CommentIdentity {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw) as Partial<CommentIdentity>;
      if (parsed.userId && parsed.userSecret) {
        return {
          userId: parsed.userId,
          userSecret: parsed.userSecret,
          displayName: parsed.displayName ?? "",
        };
      }
    }
  } catch {
    /* ignore corrupt localStorage */
  }
  const identity = {
    userId: randomToken(),
    userSecret: randomToken(),
    displayName: "",
  };
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(identity));
  } catch {
    /* ignore */
  }
  return identity;
}

function saveIdentity(identity: CommentIdentity) {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(identity));
  } catch {
    /* ignore */
  }
}

function errorLabel(error: string, t: ReturnType<typeof useTranslations>) {
  switch (error) {
    case "display_name_required":
      return t("comments.errors.displayNameRequired");
    case "body_required":
      return t("comments.errors.bodyRequired");
    case "body_too_long":
      return t("comments.errors.bodyTooLong");
    case "links_not_allowed":
      return t("comments.errors.linksNotAllowed");
    case "blocked_language":
      return t("comments.errors.blockedLanguage");
    case "rate_limited_recent":
    case "rate_limited_daily":
      return t("comments.errors.rateLimited");
    case "user_not_allowed":
      return t("comments.errors.userNotAllowed");
    default:
      return t("comments.errors.generic");
  }
}

export function CommentsPanel({ item }: CommentsPanelProps) {
  const t = useTranslations();
  const locale = useLocale();
  const [open, setOpen] = useState(false);
  const [comments, setComments] = useState<CommentItem[] | null>(null);
  const [identity, setIdentity] = useState<CommentIdentity | null>(null);
  const [displayName, setDisplayName] = useState("");
  const [body, setBody] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open || identity) return;
    const next = readIdentity();
    setIdentity(next);
    setDisplayName(next.displayName);
  }, [identity, open]);

  useEffect(() => {
    if (!open || comments !== null) return;
    let cancelled = false;
    fetchComments(item.id)
      .then((response) => {
        if (!cancelled) setComments(response.comments);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      });
    return () => {
      cancelled = true;
    };
  }, [comments, item.id, open]);

  const countLabel = useMemo(() => {
    if (comments === null) return t("comments.toggle");
    return t("comments.toggleWithCount", { count: comments.length });
  }, [comments, t]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!identity || busy) return;
    setBusy(true);
    setError(null);
    const nextIdentity = { ...identity, displayName: displayName.trim() };
    try {
      const result = await createComment({
        newsItemId: item.id,
        displayName: nextIdentity.displayName,
        body,
        userId: nextIdentity.userId,
        userSecret: nextIdentity.userSecret,
      });
      saveIdentity(nextIdentity);
      setIdentity(nextIdentity);
      setComments((previous) => [result.comment, ...(previous ?? [])]);
      setBody("");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mt-4 border-t border-slate-100 pt-3 dark:border-slate-800">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="text-[11px] font-semibold uppercase tracking-wide text-slate-500 transition-colors hover:text-indigo-600 focus-visible:outline-2 focus-visible:outline-indigo-500 dark:text-slate-400 dark:hover:text-indigo-300"
        aria-expanded={open}
      >
        {open ? t("comments.hide") : countLabel}
      </button>

      {open && (
        <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50/70 p-3 dark:border-slate-800 dark:bg-slate-950/40">
          <p className="mb-3 text-xs text-slate-500 dark:text-slate-400">
            {t("comments.policy")}
          </p>
          {comments === null ? (
            <p className="text-xs text-slate-500">{t("comments.loading")}</p>
          ) : comments.length === 0 ? (
            <p className="mb-3 text-xs text-slate-500">{t("comments.empty")}</p>
          ) : (
            <ul className="mb-4 space-y-3">
              {comments.map((comment) => (
                <li key={comment.id} className="rounded-md bg-white p-3 text-sm shadow-sm dark:bg-slate-900">
                  <div className="mb-1 flex items-center justify-between gap-3 text-xs text-slate-500">
                    <span className="font-semibold text-slate-700 dark:text-slate-200">
                      {comment.displayName}
                    </span>
                    <time dateTime={comment.createdAt}>
                      {new Intl.DateTimeFormat(locale, {
                        dateStyle: "short",
                        timeStyle: "short",
                      }).format(new Date(comment.createdAt))}
                    </time>
                  </div>
                  <p className="whitespace-pre-wrap break-words text-slate-700 dark:text-slate-200">
                    {comment.body}
                  </p>
                </li>
              ))}
            </ul>
          )}

          <form onSubmit={handleSubmit} className="space-y-2">
            <input
              type="text"
              value={displayName}
              onChange={(event) => setDisplayName(event.target.value)}
              maxLength={40}
              placeholder={t("comments.displayName")}
              className="w-full rounded border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900"
            />
            <textarea
              value={body}
              onChange={(event) => setBody(event.target.value)}
              maxLength={1000}
              rows={3}
              placeholder={t("comments.body")}
              className="w-full resize-y rounded border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900"
            />
            {error && (
              <p className="text-xs text-red-700 dark:text-red-300">
                {errorLabel(error, t)}
              </p>
            )}
            <div className="flex items-center justify-between gap-3">
              <span className="text-[11px] text-slate-500">
                {t("comments.remaining", { count: 1000 - body.length })}
              </span>
              <button
                type="submit"
                disabled={busy}
                className="rounded bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white transition-colors hover:bg-indigo-700 disabled:opacity-50 dark:bg-slate-100 dark:text-slate-900"
              >
                {busy ? t("comments.sending") : t("comments.submit")}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
