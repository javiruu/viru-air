/** @type {import('next').NextConfig} */
const localApiOrigin = (process.env.NEXT_PUBLIC_LOCAL_API_ORIGIN || "http://127.0.0.1:8000").replace(/\/$/, "");
const distDir = process.env.NEXT_DIST_DIR?.trim() || ".next";

const nextConfig = {
  reactStrictMode: true,
  distDir,
  allowedDevOrigins: ["localhost", "127.0.0.1"],
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${localApiOrigin}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
