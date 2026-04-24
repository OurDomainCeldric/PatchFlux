import Link from "next/link";
import { getLocale, getTranslations } from "next-intl/server";

export async function SiteFooter() {
  const t = await getTranslations();
  const locale = await getLocale();

  return (
    <footer className="border-t border-zinc-200 bg-zinc-50 dark:border-zinc-800 dark:bg-zinc-900">
      <div className="mx-auto w-full max-w-5xl space-y-3 px-4 py-6 text-xs text-zinc-600 dark:text-zinc-400">
        <p>{t("footer.disclaimer")}</p>
        <p>{t("footer.legalNotice")}</p>
        <nav className="flex flex-wrap gap-4" aria-label="Legal">
          <Link href={`/${locale}`} className="hover:underline">
            {t("nav.news")}
          </Link>
          <Link href={`/${locale}/sources`} className="hover:underline">
            {t("nav.sources")}
          </Link>
          <Link href={`/${locale}/imprint`} className="hover:underline">
            {t("footer.imprint")}
          </Link>
          <Link href={`/${locale}/privacy`} className="hover:underline">
            {t("footer.privacy")}
          </Link>
          <a
            href="/api/feed.xml"
            className="hover:underline"
            rel="alternate"
            type="application/rss+xml"
          >
            {t("footer.rss")}
          </a>
        </nav>
      </div>
    </footer>
  );
}
