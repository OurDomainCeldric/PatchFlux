import Link from "next/link";
import { getLocale, getTranslations } from "next-intl/server";
import { AdminNavLink } from "@/components/AdminNavLink";
import { NavLink } from "@/components/NavLink";
import { ThemeToggle } from "@/components/ThemeToggle";

export async function SiteHeader() {
  const t = await getTranslations();
  const currentLocale = await getLocale();

  return (
    <header className="sticky top-0 z-40 border-b border-slate-200/60 bg-white/70 backdrop-blur-xl dark:border-slate-800/60 dark:bg-[#09090b]/70 supports-[backdrop-filter]:bg-white/60">
      <h1 className="sr-only">{t("common.brand")}</h1>
      <div className="mx-auto flex w-full max-w-5xl flex-row items-center justify-between gap-3 px-4 py-4">
        <div className="flex items-center gap-4">
          <Link href={`/${currentLocale}`} className="flex flex-col group">
            <span className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">{t("common.brand")}</span>
            <span className="text-xs font-medium text-slate-500 dark:text-slate-400">{t("common.tagline")}</span>
          </Link>
          <div className="flex">
            <ThemeToggle />
          </div>
        </div>
        <nav className="flex items-center gap-3 text-sm" aria-label="Primary">
          <AdminNavLink href={`/${currentLocale}/admin`} label={t("nav.admin")} />
        </nav>
      </div>
    </header>
  );
}
