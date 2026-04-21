import { Suspense } from "react";
import { setRequestLocale } from "next-intl/server";
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
  const pathname = `/${locale}`;

  return (
    <Suspense fallback={null}>
      <ErrorBoundary>
        <HotTicker />
      </ErrorBoundary>
      <ErrorBoundary>
        <FilterBar pathname={pathname} />
      </ErrorBoundary>
      <ErrorBoundary>
        <NewsList pathname={pathname} />
      </ErrorBoundary>
    </Suspense>
  );
}
