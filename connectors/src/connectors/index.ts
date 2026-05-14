import type { Connector } from "../types.js";
import { remoteOkConnector } from "./remoteok.js";
import { gupyConnector } from "./gupy.js";
import { indeedConnector } from "./indeed.js";

// Conectores por API/RSS (sem scraping). Os scraper-based (LinkedIn, Vagas, Catho,
// Glassdoor, Infojobs) entram nas próximas iterações usando Browserless.
export const connectors: Record<string, Connector> = {
  [remoteOkConnector.source]: remoteOkConnector,
  [gupyConnector.source]: gupyConnector,
  [indeedConnector.source]: indeedConnector,
};

export const connectorList = Object.values(connectors);
