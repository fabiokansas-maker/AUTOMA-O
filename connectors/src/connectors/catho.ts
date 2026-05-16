import type { Connector, FetchOptions, Job } from "../types.js";
import { loadProfile } from "../profile.js";
import { withPage, jitter } from "../browserless.js";
import { parseSalaryBRL } from "../salary.js";

const BASE = "https://www.catho.com.br";

export const cathoConnector: Connector = {
  source: "catho",

  async fetchJobs(opts: FetchOptions): Promise<Job[]> {
    const profile = loadProfile();
    const queries = opts.query ? [opts.query] : profile.keywords.slice(0, 4);
    const location = opts.location ?? profile.baseCity.split("-")[0];

    const seen = new Map<string, Job>();
    for (const q of queries) {
      const url = `${BASE}/vagas/${encodeURIComponent(q.replace(/\s+/g, "-").toLowerCase())}/${encodeURIComponent(location.replace(/\s+/g, "-").toLowerCase())}/`;
      const items = await withPage({}, async (page) => {
        await page.goto(url, { waitUntil: "domcontentloaded", timeout: 45000 });
        await jitter();
        return (await page.$$eval("article[data-testid='job-card']", (els) =>
          els.map((el) => {
            const link = el.querySelector<HTMLAnchorElement>("a[href*='/vagas/']");
            const href = link?.href ?? "";
            const m = href.match(/\/vagas\/(\d+)\//);
            const externalId = m ? m[1] : href;
            const title = el.querySelector("h2, h3")?.textContent?.trim() ?? "";
            const company = el.querySelector("[data-testid='company-name']")?.textContent?.trim() ?? "";
            const loc = el.querySelector("[data-testid='location']")?.textContent?.trim() ?? "";
            const salary = el.querySelector("[data-testid='salary']")?.textContent?.trim() ?? "";
            return { externalId, title, company, location: loc, url: href, salary };
          }),
        )) as Array<{ externalId: string; title: string; company: string; location: string; url: string; salary: string }>;
      });
      for (const it of items) {
        if (!it.externalId || !it.title || !it.url) continue;
        const parsedSalary = parseSalaryBRL(it.salary);
        if (parsedSalary?.max && parsedSalary.max < profile.salaryMinBrl) continue;
        seen.set(it.externalId, {
          source: "catho",
          externalId: it.externalId,
          title: it.title,
          company: it.company || undefined,
          location: it.location || undefined,
          salaryMin: parsedSalary?.min,
          salaryMax: parsedSalary?.max,
          salaryCurrency: parsedSalary?.currency,
          url: it.url,
          applyUrl: it.url,
          description: it.salary || undefined,
          raw: it,
        });
      }
    }
    return Array.from(seen.values()).slice(0, opts.limit ?? 100);
  },
};
