import { request } from "undici";
import type { Connector, FetchOptions, Job } from "../types.js";

// Indeed RSS por busca: https://br.indeed.com/rss?q=<query>&l=<location>
// RSS retorna XML simples; parseamos sem libs externas.
const ENDPOINT = "https://br.indeed.com/rss";

function extractTag(xml: string, tag: string): string | undefined {
  const re = new RegExp(`<${tag}[^>]*>([\\s\\S]*?)<\\/${tag}>`, "i");
  const m = xml.match(re);
  if (!m) return undefined;
  return m[1].replace(/^<!\[CDATA\[/, "").replace(/\]\]>$/, "").trim();
}

function splitItems(xml: string): string[] {
  const items: string[] = [];
  const re = /<item>([\s\S]*?)<\/item>/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(xml)) !== null) items.push(m[1]);
  return items;
}

export const indeedConnector: Connector = {
  source: "indeed",
  async fetchJobs(opts: FetchOptions): Promise<Job[]> {
    const params = new URLSearchParams();
    if (opts.query) params.set("q", opts.query);
    if (opts.location) params.set("l", opts.location);

    const res = await request(`${ENDPOINT}?${params}`, {
      headers: { "User-Agent": "automa-o/0.1", Accept: "application/rss+xml" },
    });
    if (res.statusCode !== 200) throw new Error(`Indeed RSS returned ${res.statusCode}`);
    const xml = await res.body.text();
    const since = opts.since?.getTime() ?? 0;

    return splitItems(xml)
      .map((item): Job | null => {
        const url = extractTag(item, "link");
        const title = extractTag(item, "title");
        if (!url || !title) return null;
        const guid = extractTag(item, "guid") ?? url;
        const pubDate = extractTag(item, "pubDate");
        const postedAt = pubDate ? new Date(pubDate).toISOString() : undefined;
        if (since && postedAt && new Date(postedAt).getTime() < since) return null;
        const description = extractTag(item, "description");
        return {
          source: "indeed",
          externalId: guid,
          title,
          url,
          applyUrl: url,
          postedAt,
          description,
          raw: { xml: item },
        };
      })
      .filter((j): j is Job => j !== null)
      .slice(0, opts.limit ?? 50);
  },
};
