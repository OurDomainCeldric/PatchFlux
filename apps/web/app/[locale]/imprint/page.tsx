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

      <h2>{t("headingResponsible")}</h2>
      <p>
        <strong>{t("operatorLabel")}:</strong> {displayValue(operator.fullName)}
      </p>
      <p>
        <strong>{t("addressLabel")}:</strong>
        <br />
        {displayValue(operator.street)}
        <br />
        {`${displayValue(operator.postalCode)} ${displayValue(operator.city)}`.trim()}
        <br />
        {displayValue(operator.country)}
      </p>

      <h2>{t("contactHeading")}</h2>
      <p>
        <strong>{t("emailLabel")}:</strong>{" "}
        {emailIsReal ? (
          <a href={`mailto:${operator.contactEmail}`}>{operator.contactEmail}</a>
        ) : (
          displayValue(operator.contactEmail)
        )}
      </p>
      <p>
        <strong>{t("secondContactLabel")}:</strong>{" "}
        <a href={`mailto:${operator.secondContactEmail}`}>
          {operator.secondContactEmail}
        </a>
      </p>
      <p>
        <strong>{t("vatLabel")}:</strong>{" "}
        {operator.vatId ? operator.vatId : t("vatNone")}
      </p>

      <h2>{t("mstvHeading")}</h2>
      <p className="text-sm text-zinc-600 dark:text-zinc-400">{t("mstvHint")}</p>
      <p>
        {displayValue(operator.mstvResponsibleName)}
        <br />
        {displayValue(operator.mstvResponsibleAddress)}
      </p>

      <h2>{t("liabilityHeading")}</h2>
      <p>{t("liabilityBody")}</p>

      <h2>{t("trademarksHeading")}</h2>
      <p>{t("trademarksBody")}</p>

      <h2>{t("takedownHeading")}</h2>
      <p>{t("takedownBody")}</p>

      <h2>{t("disputeHeading")}</h2>
      <p>{t("disputeBody")}</p>
    </article>
  );
}

