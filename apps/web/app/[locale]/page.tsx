import { setRequestLocale } from "next-intl/server";
import { NewsList } from "@/components/NewsList";

export default async function HomePage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);

  return <NewsList />;
}
