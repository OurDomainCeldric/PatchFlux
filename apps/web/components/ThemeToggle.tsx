"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";

type Theme = "light" | "dark" | "system";

const STORAGE_KEY = "patchflux:theme";

function applyTheme(theme: Theme) {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  const prefersDark =
    theme === "dark" ||
    (theme === "system" &&
      window.matchMedia("(prefers-color-scheme: dark)").matches);
  root.classList.toggle("dark", prefersDark);
  root.dataset.theme = theme;
}

export function ThemeToggle() {
  const t = useTranslations("common");
  const [theme, setTheme] = useState<Theme>("system");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const stored = (localStorage.getItem(STORAGE_KEY) as Theme | null) ?? "system";
    setTheme(stored);
    applyTheme(stored);
    setMounted(true);

    const mql = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = () => {
      if ((localStorage.getItem(STORAGE_KEY) as Theme | null) === "system") {
        applyTheme("system");
      }
    };
    mql.addEventListener("change", handler);
    return () => mql.removeEventListener("change", handler);
  }, []);

  if (!mounted) {
    // Avoid hydration mismatch — render a neutral placeholder button.
    return (
      <button
        type="button"
        aria-hidden
        className="flex h-8 w-8 items-center justify-center rounded-full text-zinc-400 opacity-0"
      >
        <span className="sr-only">…</span>
      </button>
    );
  }

  const isDark = theme === "dark" || (theme === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);

  const toggleTheme = () => {
    const next = isDark ? "light" : "dark";
    setTheme(next);
    localStorage.setItem(STORAGE_KEY, next);
    applyTheme(next);
  };

  return (
    <button
      type="button"
      onClick={toggleTheme}
      className="flex h-8 w-8 items-center justify-center rounded-full text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900 focus-visible:outline-2 focus-visible:outline-indigo-500 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-zinc-100 transition-colors"
      title={t("toggleTheme")}
      aria-label={t("toggleTheme")}
    >
      {isDark ? (
        <svg xmlns="http://www.w3.org/2005/svg" viewBox="0 0 24 24" fill="currentColor" className="h-5 w-5 text-amber-400">
          <path d="M12 2.25a8.25 8.25 0 0 0-4.135 15.39c.686.398 1.115 1.008 1.135 1.623a.75.75 0 0 0 .75.737h4.5a.75.75 0 0 0 .75-.736c.02-.615.449-1.225 1.135-1.623A8.25 8.25 0 0 0 12 2.25ZM12 21a1.5 1.5 0 0 0 1.415-1h-2.83A1.5 1.5 0 0 0 12 21Z" />
        </svg>
      ) : (
        <svg xmlns="http://www.w3.org/2005/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="h-5 w-5">
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 18v-5.25m0 0a6.01 6.01 0 0 0 1.5-.189m-1.5.189a6.01 6.01 0 0 1-1.5-.189m3.75 7.478a12.06 12.06 0 0 1-4.5 0m3.75 2.383a14.406 14.406 0 0 1-3 0M14.25 18v-.192c0-.983.658-1.829 1.508-2.316a7.5 7.5 0 1 0-7.516 0c.85.487 1.508 1.333 1.508 2.316V18" />
        </svg>
      )}
    </button>
  );
}
