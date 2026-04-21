import type { MetadataRoute } from "next";
import { locales } from "@/i18n/config";

export const dynamic = "force-static";

const SITE_URL = (process.env.NEXT_PUBLIC_SITE_URL ?? "https://patchflux.com").replace(/\/$/, "");
const PAGES = ["", "/sources", "/imprint", "/privacy"];

export default function sitemap(): MetadataRoute.Sitemap {
  const now = new Date().toISOString();
  const entries: MetadataRoute.Sitemap = [];
  for (const locale of locales) {
    for (const page of PAGES) {
      entries.push({
        url: `${SITE_URL}/${locale}${page}`,
        lastModified: now,
        changeFrequency: page === "" ? "hourly" : "monthly",
        priority: page === "" ? 1.0 : 0.5,
      });
    }
  }
  return entries;
}
