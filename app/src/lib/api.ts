/**
 * Cliente dos agentes. É a ÚNICA porta do app para dados financeiros.
 *
 * O app não fala com banco, não monta SQL e não manda user_id: quem diz de
 * quem é o dado é o token, no backend. Aqui só viaja a pergunta e o agente.
 */
import type { Block } from '../components/blocks';

export interface AgentReply {
  threadId: string;
  messageId: string;
  blocks: Block[];
  tools: Array<{ name: string; ok: boolean; error?: string }>;
}

export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
    this.name = 'ApiError';
  }
}

export interface Sessao {
  /** token do usuário autenticado; nunca é montado no cliente */
  accessToken: string;
  baseUrl: string;
}

const TIMEOUT_MS = 30_000;

async function chamar<T>(s: Sessao, rota: string, corpo: unknown): Promise<T> {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
  try {
    const r = await fetch(`${s.baseUrl}/${rota}`, {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        authorization: `Bearer ${s.accessToken}`,
      },
      body: JSON.stringify(corpo),
      signal: ctrl.signal,
    });
    const texto = await r.text();
    if (!r.ok) {
      // a mensagem do servidor não vai crua para a tela: pode carregar detalhe
      // que o usuário não precisa ver
      throw new ApiError(mensagemDeStatus(r.status), r.status);
    }
    return JSON.parse(texto) as T;
  } catch (e) {
    if (e instanceof ApiError) throw e;
    if ((e as { name?: string }).name === 'AbortError') {
      throw new ApiError('timeout', 408);
    }
    throw new ApiError('rede', 0);
  } finally {
    clearTimeout(t);
  }
}

function mensagemDeStatus(status: number): string {
  if (status === 401) return 'sessao_expirada';
  if (status === 403) return 'sem_permissao';
  if (status === 429) return 'muitas_requisicoes';
  return 'erro_servidor';
}

export const api = {
  perguntar: (s: Sessao, p: {
    agentId: string; message: string; threadId?: string; confirmed?: boolean;
  }) => chamar<AgentReply>(s, 'kansas-agent', p),

  feedback: (s: Sessao, p: {
    messageId: string; verdict: 'helpful' | 'not_helpful' | 'report';
    category?: string; reason?: string;
  }) => chamar<{ ok: true }>(s, 'kansas-feedback', p),

  /** limpar conversa · limpar memória do agente · excluir conta */
  apagar: (s: Sessao, p: { scope: 'threads' | 'memories' | 'all'; agentId?: string }) =>
    chamar<{ threads_deleted: number; memories_deleted: number }>(s, 'kansas-purge', p),
};
