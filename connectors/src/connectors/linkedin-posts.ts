import type { Connector, FetchOptions, Job } from "../types.js";
import { loadProfile } from "../profile.js";
import { withPage, jitter } from "../browserless.js";

const LI_AT = () => process.env.LINKEDIN_LI_AT;
const UA = () => process.env.LINKEDIN_USER_AGENT ?? "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36";

function loginCookie() {
  const v = LI_AT();
  if (!v) throw new Error("LINKEDIN_LI_AT cookie not set in env");
  return [{ name: "li_at", value: v, domain: ".linkedin.com", path: "/" }];
}

// Heurística inicial: post tem "estamos contratando" / "vaga aberta" / "buscamos"
// + alguma das keywords do perfil. Validação fina fica pro LLM no matcher.
const POST_HIRING_REGEX = /\b(estamos\s+contratando|vaga\s+aberta|buscamos|procura(?:mos|ndo)|temos\s+vaga|hiring)\b/i;

interface LIPost {
  externalId: string;
  text: string;
  authorName: string;
  authorUrl: string;
  postUrl: string;
  publishedAt?: string;
}

export const linkedinPostsConnector: Connector = {
  source: "linkedin-posts",

  async fetchJobs(opts: FetchOptions): Promise<Job[]> {
    const profile = loadProfile();
    const queries = opts.query
      ? [opts.query]
      : profile.keywords.slice(0, 3).map((k) => `"estamos contratando" ${k}`);

    const allPosts = new Map<string, LIPost>();

    for (const q of queries) {
      const url = `https://www.linkedin.com/search/results/content/?keywords=${encodeURIComponent(q)}&datePosted=%22past-week%22&sortBy=%22date_posted%22`;
      const posts = await withPage({ cookies: loginCookie(), userAgent: UA() }, async (page) => {
        await page.goto(url, { waitUntil: "domcontentloaded", timeout: 45000 });
        await jitter(2000, 4000);
        for (let i = 0; i < 4; i++) {
          await page.mouse.wheel(0, 2500);
          await jitter(1200, 2500);
        }
        return (await page.$$eval("[data-urn^='urn:li:activity:']", (els) =>
          els
            .map((el) => {
              const urn = el.getAttribute("data-urn") ?? "";
              const externalId = urn.split(":").pop() ?? "";
              const text = (el.querySelector(".feed-shared-update-v2__description, .update-components-text")?.textContent ?? "").trim();
              const author = el.querySelector<HTMLAnchorElement>("a.update-components-actor__meta-link, a[data-tracking-control-name*='actor']");
              const authorName = (el.querySelector(".update-components-actor__title")?.textContent ?? "").trim();
              const authorUrl = author?.href ?? "";
              const datetime = (el.querySelector<HTMLTimeElement>("time")?.dateTime as string) ?? undefined;
              const postUrl = `https://www.linkedin.com/feed/update/${urn}/`;
              return { externalId, text, authorName, authorUrl, postUrl, publishedAt: datetime };
            })
            .filter((p) => p.externalId && p.text.length > 30),
        )) as LIPost[];
      });
      for (const p of posts) allPosts.set(p.externalId, p);
    }

    const since = opts.since?.getTime() ?? 0;
    return Array.from(allPosts.values())
      .filter((p) => POST_HIRING_REGEX.test(p.text))
      .map((p): Job => ({
        source: "linkedin-posts",
        externalId: p.externalId,
        title: p.text.slice(0, 80).replace(/\n/g, " "),
        company: p.authorName,
        location: "—",
        remote: /remoto|remote|home\s*office/i.test(p.text),
        postedAt: p.publishedAt,
        url: p.postUrl,
        description: p.text,
        raw: p,
      }))
      .filter((j) => !since || !j.postedAt || new Date(j.postedAt).getTime() >= since)
      .slice(0, opts.limit ?? 50);
  },
};
