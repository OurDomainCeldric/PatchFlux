import { setRequestLocale } from "next-intl/server";
import { RoadmapExplorer } from "@/components/RoadmapExplorer";

export default async function RoadmapPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  setRequestLocale(locale);
  return <RoadmapExplorer />;
}
