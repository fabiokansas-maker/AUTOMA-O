// Pool Postgres compartilhado. Usado por /applications e por endpoints que
// precisam consultar o histórico (rate-limit de auto-apply, etc).
import pg from "pg";

let pool: pg.Pool | null = null;

export function getPool(): pg.Pool {
  if (pool) return pool;
  const url = process.env.POSTGRES_URL;
  if (!url) throw new Error("POSTGRES_URL not set");
  pool = new pg.Pool({ connectionString: url, max: 5 });
  return pool;
}
