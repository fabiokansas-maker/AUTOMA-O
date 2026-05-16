// Perfil do candidato lido do .env. Usado pra filtros padrão (raio geográfico,
// salário mínimo, empresas-alvo, keywords) quando o conector é chamado sem
// query explícita.

export interface Profile {
  baseCity: string;
  baseLat: number;
  baseLon: number;
  maxDistanceKm: number;
  salaryMinBrl: number;
  keywords: string[];
  targetCompanies: string[];
}

function splitCsv(s: string | undefined): string[] {
  return (s ?? "")
    .split(",")
    .map((x) => x.trim().toLowerCase())
    .filter(Boolean);
}

export function loadProfile(): Profile {
  return {
    baseCity: process.env.PROFILE_BASE_CITY ?? "Diadema-SP",
    baseLat: Number(process.env.PROFILE_BASE_LAT ?? "-23.6858"),
    baseLon: Number(process.env.PROFILE_BASE_LON ?? "-46.6228"),
    maxDistanceKm: Number(process.env.PROFILE_MAX_DISTANCE_KM ?? "30"),
    salaryMinBrl: Number(process.env.PROFILE_SALARY_MIN_BRL ?? "5000"),
    keywords: splitCsv(process.env.PROFILE_KEYWORDS),
    targetCompanies: splitCsv(process.env.PROFILE_TARGET_COMPANIES),
  };
}
