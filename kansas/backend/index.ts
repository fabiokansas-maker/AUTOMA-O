/**
 * Edge Function `kansas-agent` — a única porta que o app conhece.
 *
 * O app NÃO fala com o banco. O schema `kansas` fica fora dos "Exposed
 * schemas" do Supabase, então o PostgREST não serve essas tabelas para o
 * cliente. Quem segura a conexão SQL é este arquivo.
 *
 * Fluxo de uma pergunta:
 *   JWT -> AgentRequestContext -> set_agent (valida no registry)
 *        -> contexto MÍNIMO (fatos liberados + memória do agente + inbox)
 *        -> loop de tools (só as do registry, com validação)
 *        -> blocos TIPADOS de volta -> persiste -> audita
 */
import { AgentRegistry } from "./registry.ts";
import { AuthError, buildContext, SESSION_PREAMBLE } from "./context.ts";
import { TOOLS, ToolNotAllowedError, ValidationError } from "./tools/index.ts";
import type { FinanceServices } from "./tools/finance.ts";

import { type Block, BLOCK_TYPES, sanitizarBlocos } from "./blocks.ts";
export { type Block, BLOCK_TYPES, sanitizarBlocos };

export interface Deps {
  /** roda um bloco de SQL dentro de UMA transação já carimbada */
  withSession: <T>(
    jwt: string, agentId: string,
    fn: (q: <R>(sql: string, p?: unknown[]) => Promise<R[]>) => Promise<T>,
  ) => Promise<T>;
  finance: FinanceServices;
  llm: (input: {
    system: string; messages: unknown[]; tools: unknown[];
  }) => Promise<{ blocks: Block[]; toolCalls: Array<{ name: string; args: unknown }> }>;
}

export function createHandler(deps: Deps) {
  return async function handler(req: Request): Promise<Response> {
    if (req.method !== "POST") return json({ error: "método não suportado" }, 405);

    let body: Record<string, unknown>;
    try { body = await req.json(); } catch { return json({ error: "json inválido" }, 400); }

    const agentId = String(body.agentId ?? "");
    const threadId = body.threadId ? String(body.threadId) : null;
    const pergunta = String(body.message ?? "").slice(0, 4000);
    if (!agentId || !pergunta) return json({ error: "agentId e message obrigatórios" }, 400);

    try {
      // 1) identidade — vem do token, nunca do corpo nem do modelo
      const ctxBase = await buildContext(req, agentId, String(body.sessionId ?? crypto.randomUUID()));

      return await deps.withSession(ctxBase.rawJwt, agentId, async (q) => {
        const registry = new AgentRegistry(q);
        const def = await registry.get(agentId);

        // 2) contexto MÍNIMO: só o que o registry liberou
        const [facts] = await q<{ shared_facts: Record<string, unknown> }>(
          "select kansas.shared_facts() as shared_facts",
        );
        const [mem] = await q<{ recall: Record<string, unknown> }>(
          "select kansas.recall() as recall",
        );
        const inbox = await q<{ type: string; payload: unknown }>(
          "select type, payload from kansas.inbox($1)", [5],
        );

        const ctx = { ...ctxBase, ...localeFrom(facts?.shared_facts ?? {}) };

        // 3) thread
        const thread = threadId ?? (await q<{ id: string }>(
          `insert into kansas.agent_threads (user_id, agent_id, title)
           values (auth.uid(), $1, $2) returning id`,
          [agentId, pergunta.slice(0, 60)],
        ))[0].id;

        await q(
          `insert into kansas.agent_messages (thread_id, user_id, agent_id, role, blocks)
           values ($1, auth.uid(), $2, 'user', $3::jsonb)`,
          [thread, agentId, JSON.stringify([{ type: "text", text: pergunta }])],
        );

        // 4) o modelo só recebe o que precisa
        const resposta = await deps.llm({
          system: montarSystem(def.systemInstructions, ctx, facts?.shared_facts ?? {}, mem?.recall ?? {}, inbox),
          messages: [{ role: "user", content: pergunta }],
          tools: def.allowedTools.filter((t) => t in TOOLS).map((t) => ({
            name: t,
            description: TOOLS[t].description,
          })),
        });

        // 5) tools: allowlist do registry + validação, antes de qualquer execução
        const resultados: Array<{ name: string; ok: boolean; data?: unknown; error?: string }> = [];
        for (const chamada of resposta.toolCalls.slice(0, 8)) {
          try {
            await registry.assertToolAllowed(agentId, chamada.name);
            const tool = TOOLS[chamada.name];
            if (!tool) throw new ToolNotAllowedError(`tool inexistente: ${chamada.name}`);
            const args = tool.validate(chamada.args as never);
            if (tool.requiresConfirmation && body.confirmed !== true) {
              resultados.push({ name: chamada.name, ok: false, error: "precisa_confirmacao" });
              continue;
            }
            const data = await tool.run(ctx, args as never, deps.finance);
            resultados.push({ name: chamada.name, ok: true, data });
            await audit(q, agentId, chamada.name, "allow", null);
          } catch (e) {
            const motivo = e instanceof ValidationError || e instanceof ToolNotAllowedError
              ? e.message : "falha na execução";
            resultados.push({ name: chamada.name, ok: false, error: motivo });
            await audit(q, agentId, chamada.name, "deny", motivo);
          }
        }

        const blocos = sanitizarBlocos(resposta.blocks);
        const [msg] = await q<{ id: string }>(
          `insert into kansas.agent_messages
             (thread_id, user_id, agent_id, role, blocks, tool_calls)
           values ($1, auth.uid(), $2, 'agent', $3::jsonb, $4::jsonb) returning id`,
          [thread, agentId, JSON.stringify(blocos), JSON.stringify(resultados)],
        );

        return json({ threadId: thread, messageId: msg.id, blocks: blocos, tools: resultados });
      });
    } catch (e) {
      if (e instanceof AuthError) return json({ error: "não autenticado" }, 401);
      console.error("kansas-agent:", e instanceof Error ? e.name : "erro");
      return json({ error: "erro interno" }, 500);
    }
  };
}

function montarSystem(
  instrucoes: string,
  ctx: { locale: string; currency: string; timezone: string },
  fatos: Record<string, unknown>,
  memoria: Record<string, unknown>,
  inbox: Array<{ type: string; payload: unknown }>,
): string {
  return [
    instrucoes,
    `Contexto do usuário: idioma ${ctx.locale}, moeda ${ctx.currency}, fuso ${ctx.timezone}.`,
    `Preferências liberadas: ${JSON.stringify(fatos)}`,
    `Sua memória neste domínio: ${JSON.stringify(memoria)}`,
    inbox.length ? `Avisos de outros especialistas: ${JSON.stringify(inbox)}` : "",
    "Você NUNCA calcula valores: todo número vem de uma tool. Se não tem a tool, diga que não tem acesso a esse dado.",
    "Você não dá recomendação de investimento nem aconselhamento financeiro regulado.",
  ].filter(Boolean).join("\n");
}

function localeFrom(f: Record<string, unknown>) {
  return {
    locale: typeof f.locale === "string" ? f.locale : "pt-BR",
    currency: typeof f.currency === "string" ? f.currency : "BRL",
    timezone: typeof f.timezone === "string" ? f.timezone : "America/Sao_Paulo",
  };
}

async function audit(
  q: <R>(sql: string, p?: unknown[]) => Promise<R[]>,
  agentId: string, tool: string, decision: "allow" | "deny", reason: string | null,
) {
  try {
    await q(
      `insert into kansas.audit_events (user_id, agent_id, tool, decision, reason)
       values (auth.uid(), $1, $2, $3, $4)`,
      [agentId, tool, decision, reason],
    );
  } catch { /* auditoria nunca derruba a resposta do usuário */ }
}

const json = (b: unknown, status = 200) =>
  new Response(JSON.stringify(b), { status, headers: { "content-type": "application/json" } });

export { SESSION_PREAMBLE };
