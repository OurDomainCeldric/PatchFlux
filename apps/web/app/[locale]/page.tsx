import { Suspense } from "react";
import { setRequestLocale } from "next-intl/server";
import { FilterBar } from "@/components/FilterBar";
import { NewsList } from "@/components/NewsList";

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
      <FilterBar pathname={pathname} />
      <NewsList pathname={pathname} />
    </Suspense>
  );
}
