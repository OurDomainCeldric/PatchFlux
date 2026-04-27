import { Suspense } from "react";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { COMMUNITY_TAB_ENABLED, FeedTabs } from "@/components/FeedTabs";
import { FilterBar } from "@/components/FilterBar";
import { HotTicker } from "@/components/HotTicker";
import { NewsList } from "@/components/NewsList";
import { ErrorBoundary } from "@/components/ErrorBoundary";

export default async function HomePage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("tabs");

  const pathname = `/${locale}`;

  return (
    <Suspense fallback={null}>
      <ErrorBoundary>
        <HotTicker />
      </ErrorBoundary>
      <ErrorBoundary>
        <FeedTabs pathname={pathname} />
      </ErrorBoundary>
      {!COMMUNITY_TAB_ENABLED && (
        <p className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-200">
          {t("communityTemporarilyDisabled")}
        </p>
      )}
      <ErrorBoundary>
        <FilterBar pathname={pathname} />
      </ErrorBoundary>
      <ErrorBoundary>
        <NewsList pathname={pathname} />
      </ErrorBoundary>
    </Suspense>
  );
}
