import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

const withNextIntl = createNextIntlPlugin("./i18n/request.ts");

const config: NextConfig = {
  reactStrictMode: true,
  // Static export works great with Azure Static Web Apps.
  output: "export",
  images: {
    // We do not serve third-party images (legal guardrail); disable the optimizer.
    unoptimized: true,
  },
  trailingSlash: true,
};

export default withNextIntl(config);
