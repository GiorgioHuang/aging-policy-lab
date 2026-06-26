import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Self-contained server build for a small container (Cloud Run). See Dockerfile.
  output: "standalone",
  // This app is an npm workspace; trace files from the monorepo root so the
  // standalone bundle includes workspace deps.
  outputFileTracingRoot: path.join(__dirname, "../../"),
  // `pg` is a server-only dependency; keep it out of the client bundle.
  serverExternalPackages: ["pg"],
};

export default nextConfig;
