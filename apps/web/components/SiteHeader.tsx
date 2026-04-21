import Link from "next/link";
import { getLocale, getTranslations } from "next-intl/server";
import { AdminNavLink } from "@/components/AdminNavLink";
import { NavLink } from "@/components/NavLink";
import { ThemeToggle } from "@/components/ThemeToggle";

export async function SiteHeader() {
  const t = await getTranslations();
  const currentLocale = await getLocale();

  return (
    <header className="border-b border-zinc-200 bg-white/80 backdrop-blur dark:border-zinc-800 dark:bg-zinc-900/80">
      <h1 className="sr-only">{t("common.brand")}</h1>
      <div className="mx-auto flex w-full max-w-5xl flex-wrap items-center justify-between gap-3 px-4 py-4">
        <Link href={`/${currentLocale}`} className="flex flex-col">
          <span className="text-lg font-semibold">{t("common.brand")}</span>
          <span className="text-xs text-zinc-500">{t("common.tagline")}</span>
        </Link>
        <nav className="flex flex-wrap items-center gap-3 text-sm" aria-label="Primary">
          <NavLink href={`/${currentLocale}`}>{t("nav.news")}</NavLink>
          <NavLink href={`/${currentLocale}/sources`}>{t("nav.sources")}</NavLink>
          <AdminNavLink href={`/${currentLocale}/admin`} label={t("nav.admin")} />
          <ThemeToggle />
        </nav>
      </div>
    </header>
  );
}
