import { request } from "undici";
import type { ApplyPayload, ApplyResult, Connector, FetchOptions, Job } from "../types.js";
import { loadProfile } from "../profile.js";
import { isWithinRadius } from "../geo.js";
import { parseSalaryBRL } from "../salary.js";
import { withPage, jitter } from "../browserless.js";

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

async function fetchOne(params: URLSearchParams): Promise<GupyJob[]> {
  const res = await request(`${ENDPOINT}?${params}`, {
    headers: { "User-Agent": "automa-o/0.1", Accept: "application/json" },
  });
  if (res.statusCode !== 200) throw new Error(`Gupy returned ${res.statusCode}`);
  const body = (await res.body.json()) as { data?: GupyJob[] };
  return body.data ?? [];
}

export const gupyConnector: Connector = {
  source: "gupy",

  async fetchJobs(opts: FetchOptions): Promise<Job[]> {
    const profile = loadProfile();
    const queries = opts.query ? [opts.query] : profile.keywords.length ? profile.keywords : ["controladoria"];

    // Faz uma query por keyword e une os resultados (Gupy não tem OR em "name").
    const seen = new Map<number, GupyJob>();
    for (const q of queries) {
      const params = new URLSearchParams();
      params.set("name", q);
      if (opts.location) params.set("city", opts.location);
      params.set("limit", String(opts.limit ?? 100));
      params.set("offset", "0");
      try {
        const items = await fetchOne(params);
        for (const it of items) seen.set(it.id, it);
      } catch (e) {
        // se uma keyword falha, continua nas outras
        console.error(`[gupy] keyword "${q}" failed:`, e);
      }
    }

    const since = opts.since?.getTime() ?? 0;
    const targets = profile.targetCompanies;
    const useTargetFilter = targets.length > 0 && !opts.query; // se user passou query explícita, não filtra empresa

    return Array.from(seen.values())
      .map((it): Job | null => {
        const postedAt = it.publishedDate ? new Date(it.publishedDate).toISOString() : undefined;
        if (since && postedAt && new Date(postedAt).getTime() < since) return null;

        const url = it.jobUrl ?? (it.careerPageUrl ? `${it.careerPageUrl}/job/${it.id}` : undefined);
        if (!url) return null;

        const company = it.careerPageName ?? "";
        const companyNorm = company.toLowerCase();
        if (useTargetFilter && !targets.some((t) => companyNorm.includes(t))) return null;

        const location = [it.city, it.state, it.country].filter(Boolean).join(", ") || undefined;
        // filtra por raio se temos coords (vagas remotas sempre passam)
        if (!it.isRemoteWork && location) {
          const within = isWithinRadius(location, profile.baseLat, profile.baseLon, profile.maxDistanceKm);
          if (within === false) return null;
        }

        const salary = parseSalaryBRL(it.description);
        if (salary?.max && salary.max < profile.salaryMinBrl) return null;

        return {
          source: "gupy",
          externalId: String(it.id),
          title: it.name,
          company: it.careerPageName,
          location,
          remote: Boolean(it.isRemoteWork),
          salaryMin: salary?.min,
          salaryMax: salary?.max,
          salaryCurrency: salary?.currency,
          postedAt,
          url,
          applyUrl: url,
          description: it.description,
          raw: it,
        };
      })
      .filter((j): j is Job => j !== null);
  },

  async applyJob(payload: ApplyPayload): Promise<ApplyResult> {
    // Gupy: cada empresa tem fluxo próprio mas a maioria usa formulário padronizado
    // em /candidate-position?jobId=XXX. Fluxo:
    // 1) abrir applyUrl
    // 2) clicar em "Quero me candidatar"
    // 3) preencher form (nome, email, telefone, cidade)
    // 4) upload do CV (campo accept=".pdf,.doc,.docx")
    // 5) escrever carta de apresentação no campo livre (se houver)
    // 6) confirmar e capturar texto de confirmação
    if (!payload.cvFileBase64) {
      return { status: "failed", error: "cvFileBase64 missing" };
    }
    const targetUrl = payload.applyUrl ?? payload.url;
    try {
      const result = await withPage({ userAgent: "Mozilla/5.0 (Linux) automa-o/0.1" }, async (page) => {
        await page.goto(targetUrl, { waitUntil: "domcontentloaded", timeout: 30000 });
        await jitter();
        const applyBtn = page.locator('button:has-text("candidatar"), a:has-text("candidatar")').first();
        if (!(await applyBtn.count())) {
          return { status: "external_redirect" as const, redirectUrl: targetUrl, notes: "apply button not found" };
        }
        await applyBtn.click();
        await jitter();
        // formulário básico
        await page.fill('input[name="name"], input[placeholder*="nome" i]', payload.candidate.name).catch(() => {});
        await page.fill('input[type="email"]', payload.candidate.email).catch(() => {});
        if (payload.candidate.phone) {
          await page.fill('input[type="tel"], input[placeholder*="telefone" i]', payload.candidate.phone).catch(() => {});
        }
        // upload CV
        const buf = Buffer.from(payload.cvFileBase64!, "base64");
        const fileInput = page.locator('input[type="file"]').first();
        if (await fileInput.count()) {
          await fileInput.setInputFiles({
            name: payload.cvFileName ?? "curriculo.pdf",
            mimeType: "application/pdf",
            buffer: buf,
          });
          await jitter();
        }
        // carta livre
        const coverField = page.locator('textarea[placeholder*="apresenta" i], textarea[name*="cover" i]').first();
        if (await coverField.count()) {
          await coverField.fill(payload.coverLetter);
          await jitter();
        }
        // submit
        const submit = page.locator('button[type="submit"], button:has-text("enviar"), button:has-text("Candidatar")').last();
        await submit.click();
        await page.waitForLoadState("networkidle", { timeout: 30000 }).catch(() => {});
        await jitter(2000, 4000);
        const confirmation = await page.locator('text=/parab[ée]ns|candidatura enviada|sucesso/i').first().textContent().catch(() => null);
        return {
          status: "sent" as const,
          submittedAt: new Date().toISOString(),
          notes: confirmation ?? "form submitted; no confirmation text detected",
        };
      });
      return result;
    } catch (e) {
      return { status: "failed", error: String(e) };
    }
  },
};
