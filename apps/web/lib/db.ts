import { Pool } from "pg";

// A single pooled connection, reused across hot reloads in dev.
// Reads DATABASE_URL from the environment (see .env.example).
declare global {
  // eslint-disable-next-line no-var
  var _hapiPool: Pool | undefined;
}

export const pool: Pool =
  global._hapiPool ??
  new Pool({
    connectionString: process.env.DATABASE_URL,
    // Keep the dev pool small.
    max: 5,
  });

if (process.env.NODE_ENV !== "production") {
  global._hapiPool = pool;
}
