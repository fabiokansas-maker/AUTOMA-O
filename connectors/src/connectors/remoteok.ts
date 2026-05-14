import { request } from "undici";
import type { Connector, FetchOptions, Job } from "../types.js";

const ENDPOINT = "https://remoteok.com/api";

export const remoteOkConnector: Connector = {
  source: "remoteok",
  async fetchJobs(opts: FetchOptions): Promise<Job[]> {
    const res = await request(ENDPOINT, {
      headers: { "User-Agent": "automa-o/0.1 (+https://github.com/fabiokansas-maker/automa-o)" },
    });
    if (res.statusCode !== 200) throw new Error(`RemoteOK returned ${res.statusCode}`);
    const data = (await res.body.json()) as Array<Record<string, unknown>>;

    // First element is metadata
    const items = data.slice(1);
    const since = opts.since?.getTime() ?? 0;
    const q = opts.query?.toLowerCase();

    return items
      .map((it): Job | null => {
        const id = String(it.id ?? "");
        if (!id) return null;
        const postedAt = typeof it.date === "string" ? new Date(it.date).toISOString() : undefined;
        if (since && postedAt && new Date(postedAt).getTime() < since) return null;
        const title = String(it.position ?? "");
        if (q && !title.toLowerCase().includes(q) && !String(it.description ?? "").toLowerCase().includes(q))
          return null;
        return {
          source: "remoteok",
          externalId: id,
          title,
          company: it.company ? String(it.company) : undefined,
          location: it.location ? String(it.location) : "Remote",
          remote: true,
          postedAt,
          url: String(it.url ?? `https://remoteok.com/remote-jobs/${id}`),
          applyUrl: it.apply_url ? String(it.apply_url) : undefined,
          description: it.description ? String(it.description) : undefined,
          raw: it,
        };
      })
      .filter((j): j is Job => j !== null)
      .slice(0, opts.limit ?? 100);
  },
};
