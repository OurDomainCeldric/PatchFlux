import { setRequestLocale } from "next-intl/server";
import { SourcesList } from "@/components/SourcesList";

export default async function SourcesPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);

  return <SourcesList />;
}
