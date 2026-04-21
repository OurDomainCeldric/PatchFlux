import { setRequestLocale } from "next-intl/server";
import { AdminConsole } from "@/components/AdminConsole";
import { locales } from "@/i18n/config";

export function generateStaticParams() {
  return locales.map((locale) => ({ locale }));
}

export const metadata = { robots: { index: false, follow: false } };

export default async function AdminPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  return <AdminConsole />;
}
