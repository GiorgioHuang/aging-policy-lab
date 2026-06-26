import { Pool } from "pg";

// A single pooled connection, reused across hot reloads in dev.
// Reads DATABASE_URL from the environment (see .env.example).
declare global {
  // eslint-disable-next-line no-var
  var _hapiPool: Pool | undefined;
}

const connectionString = process.env.DATABASE_URL ?? "";

// Managed Postgres (e.g. Neon) requires TLS. Neon's certificates are publicly
// trusted, so verify them (rejectUnauthorized). Local Postgres needs no SSL.
const needsSsl =
  /sslmode=require/.test(connectionString) ||
  /\.neon\.tech/.test(connectionString) ||
  process.env.PGSSL === "require";

export const pool: Pool =
  global._hapiPool ??
  new Pool({
    connectionString,
    ssl: needsSsl ? { rejectUnauthorized: true } : undefined,
    // Keep the dev pool small.
    max: 5,
  });

if (process.env.NODE_ENV !== "production") {
  global._hapiPool = pool;
}
