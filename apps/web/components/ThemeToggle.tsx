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
        className="rounded border border-zinc-300 px-2 py-1 text-xs opacity-0 dark:border-zinc-700"
      >
        …
      </button>
    );
  }

  const handleChange = (next: Theme) => {
    setTheme(next);
    localStorage.setItem(STORAGE_KEY, next);
    applyTheme(next);
  };

  return (
    <div className="flex items-center" role="group" aria-label={t("theme")}>
      <label className="sr-only" htmlFor="theme-select">
        {t("toggleTheme")}
      </label>
      <select
        id="theme-select"
        value={theme}
        onChange={(event) => handleChange(event.target.value as Theme)}
        className="rounded border border-zinc-300 bg-white px-2 py-1 text-xs dark:border-zinc-700 dark:bg-zinc-900"
      >
        <option value="system">{t("themeSystem")}</option>
        <option value="light">{t("themeLight")}</option>
        <option value="dark">{t("themeDark")}</option>
      </select>
    </div>
  );
}
