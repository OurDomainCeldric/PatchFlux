import type { Metadata } from "next";
import { setRequestLocale, getTranslations } from "next-intl/server";
import { locales } from "@/i18n/config";
import {
  PENDING_MARKER,
  displayValue,
  isOperatorConfigComplete,
  operator,
} from "@/lib/operator";

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
  const complete = isOperatorConfigComplete();
  const emailIsReal = operator.contactEmail !== PENDING_MARKER;

  return (
    <article className="prose prose-zinc max-w-none dark:prose-invert">
      <h1>{t("title")}</h1>

      {!complete && (
        <div
          role="alert"
          className="not-prose mb-6 rounded border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800 dark:border-red-800 dark:bg-red-950 dark:text-red-200"
        >
          {t("draftBanner")}
        </div>
      )}

      <p>{t("intro")}</p>

      <h2>{t("controllerHeading")}</h2>
      <p>{t("controllerIntro")}</p>
      <p>
        {displayValue(operator.fullName)}
        <br />
        {displayValue(operator.street)}
        <br />
        {`${displayValue(operator.postalCode)} ${displayValue(operator.city)}`.trim()}
        <br />
        {displayValue(operator.country)}
      </p>
      <p>
        <strong>{t("controllerContactLabel")}:</strong>{" "}
        {emailIsReal ? (
          <a href={`mailto:${operator.contactEmail}`}>{operator.contactEmail}</a>
        ) : (
          displayValue(operator.contactEmail)
        )}
      </p>

      <h2>{t("dpoHeading")}</h2>
      <p>{t("dpoBody")}</p>

      <h2>{t("dataHeading")}</h2>
      <p>{t("dataBody")}</p>

      <h2>{t("legalBasisHeading")}</h2>
      <p>{t("legalBasisBody")}</p>

      <h2>{t("retentionHeading")}</h2>
      <p>{t("retentionBody")}</p>

      <h2>{t("processorsHeading")}</h2>
      <p>{t("processorsBody")}</p>

      <h2>{t("transferHeading")}</h2>
      <p>{t("transferBody")}</p>

      <h2>{t("thirdPartyHeading")}</h2>
      <p>{t("thirdPartyBody")}</p>

      <h2>{t("rightsHeading")}</h2>
      <p>{t("rightsBody")}</p>

      <h2>{t("complaintHeading")}</h2>
      <p>{t("complaintBody")}</p>

      <h2>{t("automatedHeading")}</h2>
      <p>{t("automatedBody")}</p>

      <h2>{t("changesHeading")}</h2>
      <p>{t("changesBody")}</p>
    </article>
  );
}

