import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  transpilePackages: ["@agentic-travel-engine/shared-types"],
  allowedDevOrigins: ["127.0.0.1", "localhost"],
  async rewrites() {
    const apiOrigin = process.env.API_PROXY_ORIGIN ?? "http://127.0.0.1:8000";
    return [
      {
        source: "/api/agent/:path*",
        destination: `${apiOrigin}/api/agent/:path*`,
      },
    ];
  },
};

export default nextConfig;
