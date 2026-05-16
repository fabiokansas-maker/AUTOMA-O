// Heurística pra extrair faixa salarial de descrições em português.
// Reconhece: "R$ 5.000", "R$ 5.000,00", "R$ 5 mil", "5k", "entre 4.000 e 6.000", etc.

export interface SalaryRange {
  min?: number;
  max?: number;
  currency: "BRL";
}

const NUM = "\\d{1,3}(?:[.,]\\d{3})*(?:[.,]\\d{1,2})?";

function toNumber(raw: string, suffix?: string): number {
  // Remove pontos de milhar, troca vírgula decimal por ponto
  let n = raw.replace(/\./g, "").replace(",", ".");
  let v = Number(n);
  if (suffix && /mil|k/i.test(suffix)) v *= 1000;
  return Math.round(v);
}

export function parseSalaryBRL(text: string | undefined): SalaryRange | null {
  if (!text) return null;
  const t = text.toLowerCase();

  // "entre R$ 4.000 e R$ 6.000" / "de 4000 a 6000"
  const ranges = [
    new RegExp(`(?:entre|de)\\s*r?\\$?\\s*(${NUM})\\s*(mil|k)?\\s*(?:e|a|até)\\s*r?\\$?\\s*(${NUM})\\s*(mil|k)?`, "i"),
  ];
  for (const re of ranges) {
    const m = t.match(re);
    if (m) {
      return { min: toNumber(m[1], m[2]), max: toNumber(m[3], m[4]), currency: "BRL" };
    }
  }

  // Único valor: "salário R$ 5.000", "remuneração 5 mil", "5k"
  const single = new RegExp(`(?:sal[áa]rio|remunera[çc][ãa]o|sal\\.?)\\s*[:\\-]?\\s*r?\\$?\\s*(${NUM})\\s*(mil|k)?`, "i");
  const ms = t.match(single);
  if (ms) {
    const v = toNumber(ms[1], ms[2]);
    return { min: v, max: v, currency: "BRL" };
  }

  // Qualquer "R$ N" no texto
  const generic = new RegExp(`r\\$\\s*(${NUM})\\s*(mil|k)?`, "i");
  const mg = t.match(generic);
  if (mg) {
    const v = toNumber(mg[1], mg[2]);
    return { min: v, currency: "BRL" };
  }

  return null;
}
