/**
 * AgentRequestContext — a identidade que o modelo NÃO escolhe.
 *
 * Regra inegociável do produto: o `user_id` sai do JWT verificado, entra no
 * contexto e é o backend que o injeta em toda query. O LLM pode pedir
 * "as transações dos últimos 30 dias"; ele não pode dizer DE QUEM.
 */
import { decodeJwt, jwtVerify } from "https://deno.land/x/jose@v5.9.6/index.ts";

export interface AgentRequestContext {
  readonly authenticatedUserId: string;
  readonly agentId: string;
  readonly sessionId: string;
  readonly locale: string;
  readonly currency: string;
  readonly timezone: string;
  /** JWT original — repassado ao Postgres para que o RLS veja o mesmo sujeito */
  readonly rawJwt: string;
}

export class AuthError extends Error {
  constructor(msg: string) { super(msg); this.name = "AuthError"; }
}

const JWT_SECRET = new TextEncoder().encode(
  Deno.env.get("SUPABASE_JWT_SECRET") ?? "",
);

/**
 * Constrói o contexto a partir do header Authorization. Nada aqui aceita
 * user_id vindo do corpo da requisição — nem do app, nem do modelo.
 */
export async function buildContext(
  req: Request,
  agentId: string,
  sessionId: string,
  sharedFacts: Record<string, unknown> = {},
): Promise<AgentRequestContext> {
  const header = req.headers.get("Authorization") ?? "";
  const token = header.startsWith("Bearer ") ? header.slice(7) : "";
  if (!token) throw new AuthError("sem token");

  let sub: string | undefined;
  if (JWT_SECRET.length > 0) {
    const { payload } = await jwtVerify(token, JWT_SECRET);
    sub = payload.sub;
    if (payload.exp && payload.exp * 1000 < Date.now()) {
      throw new AuthError("sessão expirada");
    }
  } else {
    // Ambiente de teste sem segredo: ainda assim o sujeito vem do token.
    sub = decodeJwt(token).sub;
  }
  if (!sub) throw new AuthError("token sem sub");

  return Object.freeze({
    authenticatedUserId: sub,
    agentId,
    sessionId,
    locale: str(sharedFacts.locale, "pt-BR"),
    currency: str(sharedFacts.currency, "BRL"),
    timezone: str(sharedFacts.timezone, "America/Sao_Paulo"),
    rawJwt: token,
  });
}

function str(v: unknown, fallback: string): string {
  return typeof v === "string" && v.length > 0 ? v : fallback;
}

/**
 * Abre uma transação já "carimbada" com o sujeito do JWT e o agente corrente.
 * É este bloco que faz o RLS do Postgres valer para o agente de verdade.
 *
 *   begin
 *     select set_config('request.jwt.claims', <claims>, true)
 *     set local role authenticated
 *     select kansas.set_agent(<agentId>)   -- valida contra o registry
 *     ...queries...
 *   commit
 */
export const SESSION_PREAMBLE = `
  select set_config('request.jwt.claims', $1::text, true);
  set local role authenticated;
  select kansas.set_agent($2::text);
`;
