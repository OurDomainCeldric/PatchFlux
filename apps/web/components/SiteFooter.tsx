import { getTranslations } from "next-intl/server";

export async function SiteFooter() {
  const t = await getTranslations("footer");
  return (
    <footer className="border-t border-zinc-200 bg-zinc-50 dark:border-zinc-800 dark:bg-zinc-900">
      <div className="mx-auto w-full max-w-5xl space-y-3 px-4 py-6 text-xs text-zinc-600 dark:text-zinc-400">
        <p>{t("disclaimer")}</p>
        <p>{t("legalNotice")}</p>
      </div>
    </footer>
  );
}
