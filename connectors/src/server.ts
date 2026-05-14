import express, { type Request, type Response, type NextFunction } from "express";
import pino from "pino";
import pinoHttp from "pino-http";
import { connectorList, connectors } from "./connectors/index.js";
import type { FetchOptions } from "./types.js";

const log = pino({ level: process.env.LOG_LEVEL ?? "info" });
const app = express();
app.use(express.json({ limit: "1mb" }));
app.use(pinoHttp({ logger: log }));

const API_KEY = process.env.CONNECTORS_API_KEY;
app.use((req: Request, res: Response, next: NextFunction) => {
  if (req.path === "/health") return next();
  if (!API_KEY) return next(); // sem key configurada = aberto (apenas dev)
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

const port = Number(process.env.PORT ?? 3000);
app.listen(port, () => log.info({ port }, "connectors API listening"));
