import type { Connector, FetchOptions, Job } from "../types.js";
import { loadProfile } from "../profile.js";
import { withPage, jitter } from "../browserless.js";
import { parseSalaryBRL } from "../salary.js";

const BASE = "https://www.infojobs.com.br";

export const infojobsConnector: Connector = {
  source: "infojobs",

  async fetchJobs(opts: FetchOptions): Promise<Job[]> {
    const profile = loadProfile();
    const queries = opts.query ? [opts.query] : profile.keywords.slice(0, 4);
    const location = opts.location ?? profile.baseCity;

    const seen = new Map<string, Job>();
    for (const q of queries) {
      const url = `${BASE}/empregos.aspx?palabra=${encodeURIComponent(q)}&provincia=${encodeURIComponent(location)}`;
      const items = await withPage({}, async (page) => {
        await page.goto(url, { waitUntil: "domcontentloaded", timeout: 45000 });
        await jitter();
        return (await page.$$eval("div.vaga, li.vaga, article.js_vagaItem", (els) =>
          els.map((el) => {
            const link = el.querySelector<HTMLAnchorElement>("a[href*='/vagas-de-']");
            const href = link?.href ?? "";
            const m = href.match(/\/of-([a-z0-9]+)\.aspx/);
            const externalId = m ? m[1] : href;
            const title = el.querySelector("h2, h3, .h3, .titulo-da-vaga")?.textContent?.trim() ?? "";
            const company = el.querySelector(".empresa, .nome-da-empresa")?.textContent?.trim() ?? "";
            const loc = el.querySelector(".local, .vaga-local")?.textContent?.trim() ?? "";
            const salary = el.querySelector(".salario, .vaga-salario")?.textContent?.trim() ?? "";
            return { externalId, title, company, location: loc, url: href, salary };
          }),
        )) as Array<{ externalId: string; title: string; company: string; location: string; url: string; salary: string }>;
      });
      for (const it of items) {
        if (!it.externalId || !it.title || !it.url) continue;
        const parsedSalary = parseSalaryBRL(it.salary);
        if (parsedSalary?.max && parsedSalary.max < profile.salaryMinBrl) continue;
        seen.set(it.externalId, {
          source: "infojobs",
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
