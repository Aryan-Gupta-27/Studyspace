import type { NextConfig } from "next";

const apiOrigin = process.env.API_ORIGIN ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // The browser only ever talks to this origin; /api requests are proxied
  // server-side to FastAPI, so no client code needs to know the backend host.
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${apiOrigin}/api/:path*`,
      },
      {
        source: "/health",
        destination: `${apiOrigin}/health`,
      },
    ];
  },
  // Allow the hosted preview origin to talk to the dev server.
  allowedDevOrigins: ["*.e2b.app", "*.arena.ai", "localhost"],
};

export default nextConfig;
