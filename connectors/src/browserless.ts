// Cliente Playwright que conecta no Browserless via CDP.
// Usado pelos scrapers (LinkedIn, Vagas, Catho, Glassdoor, Infojobs).
// Lazy-import de playwright-core pra não pesar startup quando só usamos APIs JSON.

import type { Browser, BrowserContext, Page } from "playwright-core";

let cachedBrowser: Browser | null = null;

function browserlessWsEndpoint(): string {
  const url = process.env.BROWSERLESS_URL ?? "http://browserless:3000";
  const token = process.env.BROWSERLESS_TOKEN ?? "";
  // Browserless aceita: ws://host:port?token=XXX
  const wsHost = url.replace(/^http/, "ws");
  return `${wsHost}?token=${token}`;
}

export async function getBrowser(): Promise<Browser> {
  if (cachedBrowser?.isConnected()) return cachedBrowser;
  const pw = (await import("playwright-core")).chromium;
  cachedBrowser = await pw.connectOverCDP(browserlessWsEndpoint());
  return cachedBrowser;
}

export interface PageOpts {
  cookies?: Array<{ name: string; value: string; domain: string; path?: string }>;
  userAgent?: string;
  viewport?: { width: number; height: number };
  timezoneId?: string;
  locale?: string;
}

export async function withPage<T>(opts: PageOpts, fn: (page: Page) => Promise<T>): Promise<T> {
  const browser = await getBrowser();
  const context: BrowserContext = await browser.newContext({
    userAgent: opts.userAgent,
    viewport: opts.viewport ?? { width: 1366, height: 900 },
    locale: opts.locale ?? "pt-BR",
    timezoneId: opts.timezoneId ?? "America/Sao_Paulo",
  });
  if (opts.cookies?.length) {
    await context.addCookies(
      opts.cookies.map((c) => ({ ...c, path: c.path ?? "/", secure: true, sameSite: "Lax" as const })),
    );
  }
  const page = await context.newPage();
  try {
    return await fn(page);
  } finally {
    await context.close().catch(() => {});
  }
}

// jitter aleatório entre ações pra reduzir fingerprint de bot
export async function jitter(minMs = 800, maxMs = 3500): Promise<void> {
  const ms = minMs + Math.random() * (maxMs - minMs);
  await new Promise((r) => setTimeout(r, ms));
}
