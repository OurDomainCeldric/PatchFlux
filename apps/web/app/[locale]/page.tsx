import { Suspense } from "react";
import { setRequestLocale } from "next-intl/server";
import { FeedTabs, type FeedTab } from "@/components/FeedTabs";
import { FilterBar } from "@/components/FilterBar";
import { HotTicker } from "@/components/HotTicker";
import { NewsList } from "@/components/NewsList";
import { ErrorBoundary } from "@/components/ErrorBoundary";

export default async function HomePage({
  params,
  searchParams,
}: {
  params: Promise<{ locale: string }>;
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
}) {
  const { locale } = await params;
  const sp = await searchParams;
  setRequestLocale(locale);

  const pathname = `/${locale}`;
  const rawTab = typeof sp?.tab === "string" ? sp.tab : "news";
  const activeTab: FeedTab = rawTab === "community" ? "community" : "news";
  const isCommunity = activeTab === "community";

  return (
    <Suspense fallback={null}>
      {!isCommunity && (
        <ErrorBoundary>
          <HotTicker />
        </ErrorBoundary>
      )}
      <ErrorBoundary>
        <FeedTabs pathname={pathname} activeTab={activeTab} />
      </ErrorBoundary>
      <ErrorBoundary>
        <FilterBar pathname={pathname} community={isCommunity} />
      </ErrorBoundary>
      <ErrorBoundary>
        <NewsList pathname={pathname} community={isCommunity} />
      </ErrorBoundary>
    </Suspense>
  );
}
