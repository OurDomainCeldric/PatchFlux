import Link from "next/link";
import { getLocale, getTranslations } from "next-intl/server";
import { locales } from "@/i18n/config";

export async function SiteHeader() {
  const t = await getTranslations();
  const currentLocale = await getLocale();
  const otherLocale = locales.find((l) => l !== currentLocale) ?? "en";

  return (
    <header className="border-b border-zinc-200 dark:border-zinc-800">
      <div className="mx-auto flex w-full max-w-5xl items-center justify-between px-4 py-4">
        <Link href={`/${currentLocale}`} className="flex flex-col">
          <span className="text-lg font-semibold">{t("common.brand")}</span>
          <span className="text-xs text-zinc-500">{t("common.tagline")}</span>
        </Link>
        <nav className="flex items-center gap-4 text-sm">
          <Link href={`/${currentLocale}`} className="hover:underline">
            {t("nav.news")}
          </Link>
          <Link href={`/${currentLocale}/sources`} className="hover:underline">
            {t("nav.sources")}
          </Link>
          <Link
            href={`/${otherLocale}`}
            className="rounded border border-zinc-300 px-2 py-1 text-xs uppercase dark:border-zinc-700"
            aria-label={t("common.switchTo", { language: otherLocale.toUpperCase() })}
          >
            {otherLocale}
          </Link>
        </nav>
      </div>
    </header>
  );
}
