import type { Connector, FetchOptions, Job } from "../types.js";
import { loadProfile } from "../profile.js";
import { withPage, jitter } from "../browserless.js";
import { parseSalaryBRL } from "../salary.js";

const BASE = "https://www.vagas.com.br";

export const vagasConnector: Connector = {
  source: "vagas",

  async fetchJobs(opts: FetchOptions): Promise<Job[]> {
    const profile = loadProfile();
    const queries = opts.query ? [opts.query] : profile.keywords.slice(0, 4);
    const location = opts.location ?? profile.baseCity.replace("-SP", "");

    const seen = new Map<string, Job>();
    for (const q of queries) {
      const url = `${BASE}/vagas-de-${encodeURIComponent(q.replace(/\s+/g, "-").toLowerCase())}-em-${encodeURIComponent(location.replace(/\s+/g, "-").toLowerCase())}`;
      const items = await withPage({}, async (page) => {
        await page.goto(url, { waitUntil: "domcontentloaded", timeout: 45000 });
        await jitter();
        return (await page.$$eval("li.vaga", (els) =>
          els.map((el) => {
            const link = el.querySelector<HTMLAnchorElement>("a.link-detalhes-vaga");
            const href = link?.href ?? "";
            const m = href.match(/\/(\d+)-/);
            const externalId = m ? m[1] : href;
            const title = el.querySelector(".cargo h2 a")?.textContent?.trim() ?? "";
            const company = el.querySelector(".emprVaga")?.textContent?.trim() ?? "";
            const loc = el.querySelector(".vaga-local")?.textContent?.trim() ?? "";
            const desc = el.querySelector(".detalhes p")?.textContent?.trim() ?? "";
            return { externalId, title, company, location: loc, url: href, description: desc };
          }),
        )) as Array<{
          externalId: string;
          title: string;
          company: string;
          location: string;
          url: string;
          description: string;
        }>;
      });
      for (const it of items) {
        if (!it.externalId || !it.title || !it.url) continue;
        const salary = parseSalaryBRL(it.description);
        if (salary?.max && salary.max < profile.salaryMinBrl) continue;
        seen.set(it.externalId, {
          source: "vagas",
          externalId: it.externalId,
          title: it.title,
          company: it.company || undefined,
          location: it.location || undefined,
          salaryMin: salary?.min,
          salaryMax: salary?.max,
          salaryCurrency: salary?.currency,
          url: it.url,
          applyUrl: it.url,
          description: it.description,
          raw: it,
        });
      }
    }
    return Array.from(seen.values()).slice(0, opts.limit ?? 100);
  },
};
