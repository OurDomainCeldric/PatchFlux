import type { Metadata } from "next";
import { setRequestLocale, getTranslations } from "next-intl/server";
import { locales } from "@/i18n/config";

export function generateStaticParams() {
  return locales.map((locale) => ({ locale }));
}

export async function generateMetadata(props: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await props.params;
  const t = await getTranslations({ locale, namespace: "privacy" });
  return { title: t("title") };
}

export default async function PrivacyPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations({ locale, namespace: "privacy" });

  return (
    <article className="prose prose-zinc max-w-none dark:prose-invert">
      <h1>{t("title")}</h1>
      <p>{t("intro")}</p>
      <h2>{t("dataHeading")}</h2>
      <p>{t("dataBody")}</p>
      <h2>{t("logsHeading")}</h2>
      <p>{t("logsBody")}</p>
      <h2>{t("thirdPartyHeading")}</h2>
      <p>{t("thirdPartyBody")}</p>
      <h2>{t("rightsHeading")}</h2>
      <p>{t("rightsBody")}</p>
    </article>
  );
}
