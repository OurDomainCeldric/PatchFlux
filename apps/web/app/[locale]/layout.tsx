import type { Metadata } from "next";
import type { ReactNode } from "react";
import { notFound } from "next/navigation";
import { NextIntlClientProvider } from "next-intl";
import { getMessages, getTranslations, setRequestLocale } from "next-intl/server";
import { locales, type Locale } from "@/i18n/config";
import { Inter } from "next/font/google";
import { SiteHeader } from "@/components/SiteHeader";
import { SiteFooter } from "@/components/SiteFooter";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

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
    manifest: "/manifest.json",
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
    "https://patchflux.de"
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
    <html lang={locale} className={`${inter.variable} antialiased`}>
      <head>
        {apiOrigin && <link rel="preconnect" href={apiOrigin} crossOrigin="anonymous" />}
        <script
          type="application/ld+json"
          // eslint-disable-next-line react/no-danger
          dangerouslySetInnerHTML={{ __html: JSON.stringify(structuredData) }}
        />
        <script
          // eslint-disable-next-line react/no-danger
          dangerouslySetInnerHTML={{
            __html: `
              if ('serviceWorker' in navigator) {
                window.addEventListener('load', function() {
                  navigator.serviceWorker.register('/sw.js').then(function(registration) {
                    console.log('ServiceWorker registration successful');
                  }, function(err) {
                    console.log('ServiceWorker registration failed: ', err);
                  });
                });
              }
            `,
          }}
        />
      </head>
      <body className="bg-[#f8fafc] text-slate-900 dark:bg-[#09090b] dark:text-slate-100 font-sans selection:bg-indigo-500/30">
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
              className="mx-auto w-full max-w-5xl flex-1 px-4 py-4 sm:py-8"
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
