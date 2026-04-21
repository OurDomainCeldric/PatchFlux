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
  const t = await getTranslations({ locale, namespace: "imprint" });
  return { title: t("title") };
}

export default async function ImprintPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations({ locale, namespace: "imprint" });

  return (
    <article className="prose prose-zinc max-w-none dark:prose-invert">
      <h1>{t("title")}</h1>
      <h2>{t("headingResponsible")}</h2>
      <p>{t("operator")}</p>
      <h2>{t("contactHeading")}</h2>
      <p>{t("contactHint")}</p>
      <p className="text-sm text-zinc-500">{t("disclaimer")}</p>
    </article>
  );
}
