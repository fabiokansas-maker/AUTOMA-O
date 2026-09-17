/**
 * Kansas Router — decide QUEM responde. Não ganha acesso a nada.
 *
 * A barra "Pergunte à Kansas" da home cai aqui. O roteador escolhe o agente
 * (ou pede resumos a dois) e delega. Ele não consulta conta, fatura,
 * transação nem conversa: não tem tool própria além de roteamento.
 */
import type { AgentRegistry } from "./registry.ts";

export interface RouteDecision {
  primaryAgent: string;
  supportingAgents: string[];
  reason: string;
}

/** Sinais determinísticos primeiro; o modelo só entra no empate. */
const SINAIS: Array<[RegExp, string]> = [
  [/\bfatura|cart[aã]o|vencimento|fechamento|parcela/i, "invoices"],
  [/\bsaldo|dispon[ií]vel|quanto (eu )?tenho|conta corrente/i, "balance"],
  [/\bmeta|objetivo|guardar|juntar|viagem|sonho/i, "goals"],
  [/\bor[çc]amento|limite|categoria|gastei demais|posso gastar|quanto (eu )?posso/i, "budget"],
  [/\bcompra|transa[çc][ãa]o|extrato|lan[çc]amento|onde gastei/i, "transactions"],
  [/\bplanejar|simular|cen[áa]rio|at[ée] o fim do m[êe]s|consigo/i, "planning"],
];

export function routeBySignals(pergunta: string): RouteDecision | null {
  const hits = SINAIS.filter(([re]) => re.test(pergunta)).map(([, a]) => a);
  const unicos = [...new Set(hits)];
  if (unicos.length === 0) return null;
  if (unicos.length === 1) {
    return { primaryAgent: unicos[0], supportingAgents: [], reason: "sinal único" };
  }
  // Mais de um domínio => Planejamento coordena com RESUMOS dos outros.
  return {
    primaryAgent: "planning",
    supportingAgents: unicos.filter((a) => a !== "planning"),
    reason: "pergunta atravessa domínios; planejamento consolida resumos",
  };
}

export async function route(
  pergunta: string,
  registry: AgentRegistry,
  askModel: (p: string, opcoes: string[]) => Promise<string>,
): Promise<RouteDecision> {
  const porSinal = routeBySignals(pergunta);
  if (porSinal) return porSinal;

  const opcoes = (await registry.all()).map((a) => a.id);
  const escolhido = await askModel(pergunta, opcoes);
  return {
    primaryAgent: opcoes.includes(escolhido) ? escolhido : "planning",
    supportingAgents: [],
    reason: "classificado pelo modelo",
  };
}
