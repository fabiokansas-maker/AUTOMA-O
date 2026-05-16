import type { Connector, FetchOptions, Job } from "../types.js";
import { loadProfile } from "../profile.js";
import { isWithinRadius } from "../geo.js";
import { withPage, jitter } from "../browserless.js";

const LI_AT = () => process.env.LINKEDIN_LI_AT;
const UA = () => process.env.LINKEDIN_USER_AGENT ?? "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36";

function loginCookie() {
  const v = LI_AT();
  if (!v) throw new Error("LINKEDIN_LI_AT cookie not set in env");
  return [{ name: "li_at", value: v, domain: ".linkedin.com", path: "/" }];
}

interface LICard {
  externalId: string;
  title: string;
  company: string;
  location: string;
  url: string;
  postedAt?: string;
}

export const linkedinJobsConnector: Connector = {
  source: "linkedin-jobs",

  async fetchJobs(opts: FetchOptions): Promise<Job[]> {
    const profile = loadProfile();
    const queries = opts.query ? [opts.query] : profile.keywords.length ? profile.keywords.slice(0, 4) : ["controladoria"];
    const location = opts.location ?? profile.baseCity;

    const allCards = new Map<string, LICard>();

    for (const q of queries) {
      const url = `https://www.linkedin.com/jobs/search/?keywords=${encodeURIComponent(q)}&location=${encodeURIComponent(location)}&f_TPR=r604800&sortBy=DD`;
      const cards = await withPage(
        { cookies: loginCookie(), userAgent: UA() },
        async (page) => {
          await page.goto(url, { waitUntil: "domcontentloaded", timeout: 45000 });
          await jitter(2000, 4000);
          // scroll virtualizado pra carregar mais resultados
          for (let i = 0; i < 5; i++) {
            await page.mouse.wheel(0, 2500);
            await jitter(1200, 2500);
          }
          const parsed = await page.$$eval(
            "ul.jobs-search__results-list li, ul.scaffold-layout__list-container li.jobs-search-results__list-item",
            (els) =>
              els
                .map((el) => {
                  const link = el.querySelector<HTMLAnchorElement>('a[href*="/jobs/view/"]');
                  const href = link?.href ?? "";
                  const m = href.match(/\/jobs\/view\/(\d+)/);
                  const externalId = m ? m[1] : "";
                  const title = el.querySelector(".base-search-card__title, .job-card-list__title")?.textContent?.trim() ?? "";
                  const company = el.querySelector(".base-search-card__subtitle, .job-card-container__company-name")?.textContent?.trim() ?? "";
                  const loc = el.querySelector(".job-search-card__location, .job-card-container__metadata-item")?.textContent?.trim() ?? "";
                  const datetime = el.querySelector<HTMLTimeElement>("time")?.dateTime ?? undefined;
                  return { externalId, title, company, location: loc, url: href, postedAt: datetime };
                })
                .filter((c) => c.externalId && c.title && c.url),
          );
          return parsed as LICard[];
        },
      );
      for (const c of cards) allCards.set(c.externalId, c);
    }

    const since = opts.since?.getTime() ?? 0;
    return Array.from(allCards.values())
      .map((c): Job | null => {
        const postedAt = c.postedAt ? new Date(c.postedAt).toISOString() : undefined;
        if (since && postedAt && new Date(postedAt).getTime() < since) return null;
        const remote = /remoto|remote|home\s*office/i.test(c.location);
        if (!remote) {
          const within = isWithinRadius(c.location, profile.baseLat, profile.baseLon, profile.maxDistanceKm);
          if (within === false) return null;
        }
        return {
          source: "linkedin-jobs",
          externalId: c.externalId,
          title: c.title,
          company: c.company,
          location: c.location,
          remote,
          postedAt,
          url: c.url,
          applyUrl: c.url,
          raw: c,
        };
      })
      .filter((j): j is Job => j !== null)
      .slice(0, opts.limit ?? 100);
  },
};
