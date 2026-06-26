/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // `pg` is a server-only dependency; keep it out of the client bundle.
  serverExternalPackages: ["pg"],
};

export default nextConfig;
