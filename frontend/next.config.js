/** @type {import('next').NextConfig} */
const localApiOrigin = (process.env.NEXT_PUBLIC_LOCAL_API_ORIGIN || "http://127.0.0.1:8000").replace(/\/$/, "");

const nextConfig = {
  reactStrictMode: true,
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
