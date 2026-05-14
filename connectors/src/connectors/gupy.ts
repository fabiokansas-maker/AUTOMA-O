import { request } from "undici";
import type { Connector, FetchOptions, Job } from "../types.js";

// Gupy expõe busca pública via portais individuais (cada empresa tem seu subdomínio).
// O endpoint agregado https://portal.api.gupy.io/api/v1/jobs aceita query params.
const ENDPOINT = "https://portal.api.gupy.io/api/v1/jobs";

interface GupyJob {
  id: number;
  name: string;
  description?: string;
  jobUrl?: string;
  publishedDate?: string;
  city?: string;
  state?: string;
  country?: string;
  isRemoteWork?: boolean;
  careerPageName?: string;
  careerPageUrl?: string;
}

export const gupyConnector: Connector = {
  source: "gupy",
  async fetchJobs(opts: FetchOptions): Promise<Job[]> {
    const params = new URLSearchParams();
    if (opts.query) params.set("name", opts.query);
    if (opts.location) params.set("city", opts.location);
    params.set("limit", String(opts.limit ?? 100));
    params.set("offset", "0");

    const res = await request(`${ENDPOINT}?${params}`, {
      headers: { "User-Agent": "automa-o/0.1", Accept: "application/json" },
    });
    if (res.statusCode !== 200) throw new Error(`Gupy returned ${res.statusCode}`);
    const body = (await res.body.json()) as { data?: GupyJob[] };
    const items = body.data ?? [];
    const since = opts.since?.getTime() ?? 0;

    return items
      .map((it): Job | null => {
        const postedAt = it.publishedDate ? new Date(it.publishedDate).toISOString() : undefined;
        if (since && postedAt && new Date(postedAt).getTime() < since) return null;
        const url = it.jobUrl ?? (it.careerPageUrl ? `${it.careerPageUrl}/job/${it.id}` : undefined);
        if (!url) return null;
        return {
          source: "gupy",
          externalId: String(it.id),
          title: it.name,
          company: it.careerPageName,
          location: [it.city, it.state, it.country].filter(Boolean).join(", ") || undefined,
          remote: Boolean(it.isRemoteWork),
          postedAt,
          url,
          applyUrl: url,
          description: it.description,
          raw: it,
        };
      })
      .filter((j): j is Job => j !== null);
  },
};
