import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */

  // Enable standalone output for Docker
  output: "standalone",

  async rewrites() {
    return [
      {
        source: "/api/:path*",
        // Use environment variable for backend URL (Docker-friendly)
        destination: `${process.env.BACKEND_URL || "http://localhost:8000"}/:path*`,
      },
    ];
  },
};

export default nextConfig;
