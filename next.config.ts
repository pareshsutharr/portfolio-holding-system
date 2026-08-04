import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  turbopack: {
    root: __dirname,
  },
  async redirects() {
    return [{ source: "/", destination: "/dashboard-v2", permanent: false }];
  },
};

export default nextConfig;
