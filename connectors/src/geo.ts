// Distância geográfica (Haversine) e dicionário de cidades alvo do ABC paulista.
// Usado pra filtrar vagas dentro do raio configurado em PROFILE_MAX_DISTANCE_KM
// a partir de PROFILE_BASE_LAT/LON.

const EARTH_RADIUS_KM = 6371;

function toRad(deg: number): number {
  return (deg * Math.PI) / 180;
}

export function haversineKm(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
  return 2 * EARTH_RADIUS_KM * Math.asin(Math.sqrt(a));
}

// Dicionário (lat, lon) de cidades + bairros relevantes do ABC e SP capital.
// Quando o conector não tem lat/lon nativos, tentamos resolver pelo nome.
export const CITY_COORDS: Record<string, { lat: number; lon: number }> = {
  // ABC paulista
  "diadema": { lat: -23.6858, lon: -46.6228 },
  "diadema-sp": { lat: -23.6858, lon: -46.6228 },
  "sao bernardo do campo": { lat: -23.6914, lon: -46.5648 },
  "sao bernardo": { lat: -23.6914, lon: -46.5648 },
  "sbc": { lat: -23.6914, lon: -46.5648 },
  "santo andre": { lat: -23.6630, lon: -46.5383 },
  "sao caetano do sul": { lat: -23.6231, lon: -46.5651 },
  "sao caetano": { lat: -23.6231, lon: -46.5651 },
  "maua": { lat: -23.6677, lon: -46.4613 },
  "ribeirao pires": { lat: -23.7110, lon: -46.4136 },
  "rio grande da serra": { lat: -23.7440, lon: -46.3984 },
  // SP capital (regiões mais acessíveis de Diadema)
  "sao paulo": { lat: -23.5505, lon: -46.6333 },
  "sp": { lat: -23.5505, lon: -46.6333 },
  "sao paulo-sp": { lat: -23.5505, lon: -46.6333 },
  "sao paulo - sp": { lat: -23.5505, lon: -46.6333 },
  "santo amaro": { lat: -23.6541, lon: -46.7099 },
  "morumbi": { lat: -23.6037, lon: -46.7115 },
  "interlagos": { lat: -23.6989, lon: -46.6802 },
  "jabaquara": { lat: -23.6469, lon: -46.6428 },
  "vila olimpia": { lat: -23.5957, lon: -46.6892 },
  "berrini": { lat: -23.6128, lon: -46.6968 },
  "barueri": { lat: -23.5113, lon: -46.8763 },
  "alphaville": { lat: -23.4998, lon: -46.8459 },
  "osasco": { lat: -23.5329, lon: -46.7918 },
  // Litoral próximo (Scania tem unidade)
  "cubatao": { lat: -23.8957, lon: -46.4257 },
  "santos": { lat: -23.9619, lon: -46.3342 },
};

function normalize(name: string): string {
  return name
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/[^a-z0-9\s-]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

export function resolveCoords(locationName: string | undefined): { lat: number; lon: number } | null {
  if (!locationName) return null;
  const norm = normalize(locationName);
  // tenta match exato
  if (CITY_COORDS[norm]) return CITY_COORDS[norm];
  // tenta encontrar nome de cidade dentro da string (ex: "Analista — São Bernardo do Campo, SP")
  for (const [city, coords] of Object.entries(CITY_COORDS)) {
    if (norm.includes(city)) return coords;
  }
  return null;
}

export function isWithinRadius(
  locationName: string | undefined,
  baseLat: number,
  baseLon: number,
  maxKm: number,
): boolean | null {
  const coords = resolveCoords(locationName);
  if (!coords) return null; // não sabemos — deixa passar pro LLM decidir
  return haversineKm(baseLat, baseLon, coords.lat, coords.lon) <= maxKm;
}
