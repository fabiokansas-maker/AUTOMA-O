/**
 * Catálogo de blocos que o app sabe desenhar.
 *
 * O modelo devolve DADOS tipados, não UI livre: qualquer bloco fora do
 * catálogo é rebaixado para texto antes de chegar na tela.
 */
export const BLOCK_TYPES = [
  "text", "money_summary", "invoice_summary", "transaction_list",
  "goal_progress", "budget_status", "chart", "confirmation", "alert",
] as const;

export type BlockType = typeof BLOCK_TYPES[number];
export interface Block { type: BlockType; [k: string]: unknown }

export function sanitizarBlocos(blocks: Block[]): Block[] {
  return (blocks ?? [])
    .filter((b) => b && typeof b === "object")
    .map((b) =>
      (BLOCK_TYPES as readonly string[]).includes(b.type)
        ? b
        : { type: "text", text: String((b as { text?: string }).text ?? "") } as Block
    )
    .slice(0, 12);
}
