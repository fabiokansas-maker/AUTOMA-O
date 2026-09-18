/**
 * Formatação sensível ao país — o app roda em mais de um.
 *
 * Proibido no projeto:  "R$ " + valor
 * O domínio guarda valor + moeda; a tela formata para o contexto do usuário.
 */
export interface Money { readonly cents: number; readonly currency: string }
export interface UserLocaleContext {
  language: string;   // "pt"
  locale: string;     // "pt-BR"
  country: string;    // "BR"
  currency: string;   // "BRL"
  timezone: string;   // "America/Sao_Paulo"
}

/** Moedas sem casa decimal (JPY, KRW…) quebram divisão por 100 na mão. */
function decimais(currency: string, locale: string): number {
  try {
    const f = new Intl.NumberFormat(locale, { style: "currency", currency });
    return f.resolvedOptions().maximumFractionDigits ?? 2;
  } catch { return 2; }
}

export function formatMoney(m: Money, ctx: Pick<UserLocaleContext, "locale">): string {
  const casas = decimais(m.currency, ctx.locale);
  const valor = m.cents / Math.pow(10, casas);
  try {
    return new Intl.NumberFormat(ctx.locale, {
      style: "currency", currency: m.currency,
    }).format(valor);
  } catch {
    // moeda/locale desconhecidos: ainda assim nunca concatena "R$"
    return `${m.currency} ${valor.toFixed(casas)}`;
  }
}

export function formatDate(
  iso: string, ctx: Pick<UserLocaleContext, "locale" | "timezone">,
  opts: Intl.DateTimeFormatOptions = { day: "2-digit", month: "short", year: "numeric" },
): string {
  const d = new Date(iso.length === 10 ? `${iso}T12:00:00Z` : iso);
  if (Number.isNaN(d.getTime())) return iso;
  return new Intl.DateTimeFormat(ctx.locale, { ...opts, timeZone: ctx.timezone }).format(d);
}

/** Contexto derivado do dispositivo, sobrescrito pelo que o usuário salvou. */
export function resolveLocaleContext(
  deviceLocale: string,
  salvo: Partial<UserLocaleContext> = {},
): UserLocaleContext {
  const locale = salvo.locale || deviceLocale || "pt-BR";
  // locale pode vir vazio, só com idioma ou malformado do aparelho:
  // nada aqui pode virar undefined e explodir na formatação depois.
  const partes = locale.split("-");
  const language = partes[0] || "pt";
  const country = partes[1] || "BR";
  return {
    language: salvo.language ?? language,
    locale,
    country: salvo.country ?? country,
    currency: salvo.currency ?? moedaPadrao(country),
    timezone: salvo.timezone
      ?? Intl.DateTimeFormat().resolvedOptions().timeZone
      ?? "America/Sao_Paulo",
  };
}

const MOEDA_POR_PAIS: Record<string, string> = {
  BR: "BRL", PT: "EUR", US: "USD", GB: "GBP", ES: "EUR", MX: "MXN",
  AR: "ARS", CL: "CLP", CO: "COP", AO: "AOA", MZ: "MZN", JP: "JPY",
};
function moedaPadrao(country: string): string {
  return MOEDA_POR_PAIS[country.toUpperCase()] ?? "USD";
}
