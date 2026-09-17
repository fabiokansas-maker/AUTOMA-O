/**
 * AgentRegistry — permissões num lugar só.
 *
 * O registry é carregado do banco (kansas.agents), não de constantes
 * espalhadas pelas telas. Prompt não concede permissão; registry concede.
 */
export interface AgentDefinition {
  id: string;
  displayName: string;
  description: string;
  allowedTools: string[];
  allowedDataDomains: string[];
  readableSharedMemoryKeys: string[];
  writableMemoryScope: string[];
  readableEventTypes: string[];
  systemInstructions: string;
}

export type SqlQuery = <T>(sql: string, params?: unknown[]) => Promise<T[]>;

export class AgentRegistry {
  #cache = new Map<string, AgentDefinition>();
  #loadedAt = 0;
  constructor(private readonly query: SqlQuery, private readonly ttlMs = 60_000) {}

  async get(agentId: string): Promise<AgentDefinition> {
    await this.#refresh();
    const def = this.#cache.get(agentId);
    if (!def) throw new Error(`agente desconhecido: ${agentId}`);
    return def;
  }

  async all(): Promise<AgentDefinition[]> {
    await this.#refresh();
    return [...this.#cache.values()];
  }

  /** A checagem que roda ANTES de qualquer tool executar. */
  async assertToolAllowed(agentId: string, tool: string): Promise<void> {
    const def = await this.get(agentId);
    if (!def.allowedTools.includes(tool)) {
      throw new ToolNotAllowedError(
        `agente '${agentId}' não tem a tool '${tool}'`,
      );
    }
  }

  async #refresh(): Promise<void> {
    if (Date.now() - this.#loadedAt < this.ttlMs && this.#cache.size) return;
    const rows = await this.query<Record<string, never>>(
      `select id, display_name, description, allowed_tools, allowed_data_domains,
              readable_shared_keys, writable_memory_scope, readable_event_types,
              system_instructions
         from kansas.agents where enabled`,
    );
    this.#cache.clear();
    for (const r of rows as unknown as Array<Record<string, unknown>>) {
      this.#cache.set(r.id as string, {
        id: r.id as string,
        displayName: r.display_name as string,
        description: r.description as string,
        allowedTools: r.allowed_tools as string[],
        allowedDataDomains: r.allowed_data_domains as string[],
        readableSharedMemoryKeys: r.readable_shared_keys as string[],
        writableMemoryScope: r.writable_memory_scope as string[],
        readableEventTypes: r.readable_event_types as string[],
        systemInstructions: r.system_instructions as string,
      });
    }
    this.#loadedAt = Date.now();
  }
}

export class ToolNotAllowedError extends Error {
  constructor(msg: string) { super(msg); this.name = "ToolNotAllowedError"; }
}
