import type { Connector } from "../types.js";
import { remoteOkConnector } from "./remoteok.js";
import { gupyConnector } from "./gupy.js";
import { indeedConnector } from "./indeed.js";
import { linkedinJobsConnector } from "./linkedin-jobs.js";
import { linkedinPostsConnector } from "./linkedin-posts.js";
import { vagasConnector } from "./vagas.js";
import { cathoConnector } from "./catho.js";
import { glassdoorConnector } from "./glassdoor.js";
import { infojobsConnector } from "./infojobs.js";

export const connectors: Record<string, Connector> = {
  [remoteOkConnector.source]: remoteOkConnector,
  [gupyConnector.source]: gupyConnector,
  [indeedConnector.source]: indeedConnector,
  [linkedinJobsConnector.source]: linkedinJobsConnector,
  [linkedinPostsConnector.source]: linkedinPostsConnector,
  [vagasConnector.source]: vagasConnector,
  [cathoConnector.source]: cathoConnector,
  [glassdoorConnector.source]: glassdoorConnector,
  [infojobsConnector.source]: infojobsConnector,
};

export const connectorList = Object.values(connectors);
