import type { Connector, FetchOptions, Job } from "../types.js";
import { loadProfile } from "../profile.js";
import { withPage, jitter } from "../browserless.js";

const BASE = "https://www.glassdoor.com.br";

export const glassdoorConnector: Connector = {
  source: "glassdoor",

  async fetchJobs(opts: FetchOptions): Promise<Job[]> {
    const profile = loadProfile();
    const queries = opts.query ? [opts.query] : profile.keywords.slice(0, 3);
    const location = opts.location ?? profile.baseCity;

    const seen = new Map<string, Job>();
    for (const q of queries) {
      const url = `${BASE}/Vagas/${encodeURIComponent(location.replace(/\s+/g, "-"))}-${encodeURIComponent(q.replace(/\s+/g, "-"))}-vagas-SRCH_IL.0,15_IC2487263_KO16,40.htm`;
      const items = await withPage({}, async (page) => {
        await page.goto(url, { waitUntil: "domcontentloaded", timeout: 45000 });
        await jitter();
        return (await page.$$eval("li[data-test='jobListing']", (els) =>
          els.map((el) => {
            const link = el.querySelector<HTMLAnchorElement>("a[href*='/job-listing/']");
            const href = link?.href ?? "";
            const m = href.match(/JV_IC\d+_KO[\d,]+_KE[\d,]+\.htm\?jl=(\d+)/);
            const externalId = m ? m[1] : href;
            const title = el.querySelector("[data-test='job-title']")?.textContent?.trim() ?? "";
            const company = el.querySelector("[data-test='employer-name']")?.textContent?.trim() ?? "";
            const loc = el.querySelector("[data-test='emp-location']")?.textContent?.trim() ?? "";
            return { externalId, title, company, location: loc, url: href };
          }),
        )) as Array<{ externalId: string; title: string; company: string; location: string; url: string }>;
      });
      for (const it of items) {
        if (!it.externalId || !it.title || !it.url) continue;
        // Glassdoor BR raramente expõe salário no card; deixamos vazio.
        seen.set(it.externalId, {
          source: "glassdoor",
          externalId: it.externalId,
          title: it.title,
          company: it.company || undefined,
          location: it.location || undefined,
          url: it.url,
          applyUrl: it.url,
          raw: it,
        });
      }
    }
    return Array.from(seen.values()).slice(0, opts.limit ?? 50);
  },
};
