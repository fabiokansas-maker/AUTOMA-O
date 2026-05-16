import express, { type Request, type Response, type NextFunction } from "express";
import pino from "pino";
import pinoHttp from "pino-http";
import { connectorList, connectors } from "./connectors/index.js";
import type { ApplyPayload, FetchOptions } from "./types.js";
import { getPool } from "./db.js";

const log = pino({ level: process.env.LOG_LEVEL ?? "info" });
const app = express();
app.use(express.json({ limit: "10mb" })); // CV em base64 pode ser grande
app.use(pinoHttp({ logger: log }));

const API_KEY = process.env.CONNECTORS_API_KEY;
app.use((req: Request, res: Response, next: NextFunction) => {
  if (req.path === "/health") return next();
  if (!API_KEY) return next();
  if (req.header("x-api-key") !== API_KEY) {
    res.status(401).json({ error: "invalid api key" });
    return;
  }
  next();
});

app.get("/health", (_req, res) => {
  res.json({ ok: true, connectors: connectorList.map((c) => c.source) });
});

app.get("/connectors", (_req, res) => {
  res.json({ connectors: connectorList.map((c) => c.source) });
});

app.get("/connectors/:source", async (req: Request, res: Response) => {
  const c = connectors[req.params.source];
  if (!c) {
    res.status(404).json({ error: `unknown connector: ${req.params.source}` });
    return;
  }
  const opts: FetchOptions = {
    query: typeof req.query.q === "string" ? req.query.q : undefined,
    location: typeof req.query.location === "string" ? req.query.location : undefined,
    since: typeof req.query.since === "string" ? new Date(req.query.since) : undefined,
    limit: typeof req.query.limit === "string" ? Number(req.query.limit) : undefined,
  };
  try {
    const jobs = await c.fetchJobs(opts);
    res.json({ source: c.source, count: jobs.length, jobs });
  } catch (err) {
    req.log.error({ err, source: c.source }, "connector failed");
    res.status(502).json({ error: String(err) });
  }
});

// Submete uma candidatura programaticamente. Body = ApplyPayload.
app.post("/apply/:source", async (req: Request, res: Response) => {
  const c = connectors[req.params.source];
  if (!c) {
    res.status(404).json({ error: `unknown connector: ${req.params.source}` });
    return;
  }
  if (!c.applyJob) {
    res.status(501).json({ error: `connector ${c.source} does not support applyJob` });
    return;
  }
  const payload = req.body as ApplyPayload;
  if (!payload?.jobId || !payload.candidate?.email) {
    res.status(400).json({ error: "missing jobId or candidate.email" });
    return;
  }
  // Rate limit: máx N apps/dia por plataforma (consulta DB)
  const limit = Number(process.env.AUTO_APPLY_DAILY_LIMIT ?? "10");
  try {
    const pool = getPool();
    const { rows } = await pool.query(
      `SELECT COUNT(*)::int AS n FROM applications a
         JOIN jobs j ON j.id = a.job_id
        WHERE j.source = $1 AND a.status = 'sent'
          AND a.submitted_at >= now() - interval '24 hours'`,
      [c.source],
    );
    if (rows[0].n >= limit) {
      res.status(429).json({ error: `rate_limit_exceeded: ${rows[0].n}/${limit} apps in last 24h on ${c.source}` });
      return;
    }
  } catch (e) {
    // DB pode estar fora; deixa passar mas avisa
    req.log.warn({ err: e }, "rate limit check failed; allowing apply");
  }
  try {
    const result = await c.applyJob(payload);
    res.json(result);
  } catch (err) {
    req.log.error({ err, source: c.source }, "applyJob failed");
    res.status(500).json({ status: "failed", error: String(err) });
  }
});

// Lista applications (proxy SQL pro n8n).
app.get("/applications", async (req: Request, res: Response) => {
  const status = typeof req.query.status === "string" ? req.query.status : undefined;
  const sinceHours = typeof req.query.sinceHours === "string" ? Number(req.query.sinceHours) : 24;
  try {
    const pool = getPool();
    const { rows } = await pool.query(
      `SELECT a.id, a.status, a.submitted_at, a.error, a.cover_letter,
              j.source, j.title, j.company, j.url, j.location
         FROM applications a
         JOIN jobs j ON j.id = a.job_id
        WHERE ($1::text IS NULL OR a.status = $1::application_status)
          AND a.submitted_at >= now() - ($2 || ' hours')::interval
        ORDER BY a.submitted_at DESC NULLS LAST
        LIMIT 500`,
      [status ?? null, String(sinceHours)],
    );
    res.json({ count: rows.length, applications: rows });
  } catch (err) {
    req.log.error({ err }, "applications query failed");
    res.status(500).json({ error: String(err) });
  }
});

const port = Number(process.env.PORT ?? 3000);
app.listen(port, () => log.info({ port }, "connectors API listening"));
