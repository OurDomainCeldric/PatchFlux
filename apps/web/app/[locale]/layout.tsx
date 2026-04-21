import type { Metadata } from "next";
import type { ReactNode } from "react";
import { notFound } from "next/navigation";
import { NextIntlClientProvider } from "next-intl";
import { getMessages, getTranslations, setRequestLocale } from "next-intl/server";
import { locales, type Locale } from "@/i18n/config";
import { SiteHeader } from "@/components/SiteHeader";
import { SiteFooter } from "@/components/SiteFooter";

export function generateStaticParams() {
  return locales.map((locale) => ({ locale }));
}

export async function generateMetadata(props: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await props.params;
  const t = await getTranslations({ locale, namespace: "common" });
  return {
    title: {
      default: t("brand"),
      template: `%s · ${t("brand")}`,
    },
    description: t("tagline"),
    alternates: {
      canonical: `/${locale}`,
      languages: Object.fromEntries(locales.map((l) => [l, `/${l}`])),
    },
    openGraph: {
      type: "website",
      siteName: t("brand"),
      title: t("brand"),
      description: t("tagline"),
      locale,
    },
    twitter: {
      card: "summary_large_image",
      title: t("brand"),
      description: t("tagline"),
    },
  };
}

export default async function LocaleLayout({
  children,
  params,
}: {
  children: ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  if (!locales.includes(locale as Locale)) notFound();
  setRequestLocale(locale);

  const messages = await getMessages();
  const tCommon = await getTranslations({ locale, namespace: "common" });

  const siteUrl = (
    process.env.NEXT_PUBLIC_SITE_URL ??
    "https://witty-ocean-00e235903.7.azurestaticapps.net"
  ).replace(/\/$/, "");
  const apiBaseUrl = (
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    "https://func-omlorsnews-prod.azurewebsites.net/api"
  ).replace(/\/$/, "");
  // Derive the API origin for preconnect (strip /api and any trailing path).
  let apiOrigin = "";
  try {
    apiOrigin = new URL(apiBaseUrl).origin;
  } catch {
    apiOrigin = "";
  }

  const structuredData = {
    "@context": "https://schema.org",
    "@type": "NewsMediaOrganization",
    name: tCommon("brand"),
    description: tCommon("tagline"),
    url: `${siteUrl}/${locale}`,
    inLanguage: locale,
  };

  return (
    <html lang={locale}>
      <head>
        {apiOrigin && <link rel="preconnect" href={apiOrigin} crossOrigin="anonymous" />}
        <script
          type="application/ld+json"
          // eslint-disable-next-line react/no-danger
          dangerouslySetInnerHTML={{ __html: JSON.stringify(structuredData) }}
        />
      </head>
      <body className="bg-zinc-50 text-zinc-900 antialiased dark:bg-zinc-950 dark:text-zinc-100">
        <NextIntlClientProvider locale={locale} messages={messages}>
          <a
            href="#main-content"
            className="sr-only focus:not-sr-only focus:fixed focus:left-2 focus:top-2 focus:z-50 focus:rounded focus:bg-white focus:px-3 focus:py-2 focus:text-sm focus:text-zinc-900 focus:shadow dark:focus:bg-zinc-800 dark:focus:text-zinc-100"
          >
            {tCommon("skipToContent")}
          </a>
          <div className="flex min-h-screen flex-col">
            <SiteHeader />
            <main
              id="main-content"
              className="mx-auto w-full max-w-5xl flex-1 px-4 py-8"
            >
              {children}
            </main>
            <SiteFooter />
          </div>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
