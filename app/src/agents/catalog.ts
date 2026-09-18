/**
 * Catálogo dos agentes no app. Os ids batem com o registry do backend
 * (kansas.agents) — o app só desenha; permissão é decidida lá.
 */
export interface AgenteCard {
  id: 'balance' | 'invoices' | 'goals' | 'transactions' | 'budget' | 'planning';
  emoji: string;
  /** chaves de i18n, não texto: o app roda em vários idiomas */
  nomeChave: string;
  descChave: string;
  acoesRapidas: Array<{ id: string; chave: string }>;
}

export const AGENTES: AgenteCard[] = [
  {
    id: 'balance', emoji: '💰',
    nomeChave: 'agents.balance', descChave: 'agents.balance.desc',
    acoesRapidas: [
      { id: 'quanto_tenho', chave: 'quick.balance.now' },
      { id: 'proximos_7', chave: 'quick.balance.next7' },
    ],
  },
  {
    id: 'invoices', emoji: '💳',
    nomeChave: 'agents.invoices', descChave: 'agents.invoices.desc',
    acoesRapidas: [
      { id: 'fatura_atual', chave: 'quick.invoice.current' },
      { id: 'porque_subiu', chave: 'quick.invoice.why' },
    ],
  },
  {
    id: 'goals', emoji: '🎯',
    nomeChave: 'agents.goals', descChave: 'agents.goals.desc',
    acoesRapidas: [{ id: 'progresso', chave: 'quick.goal.progress' }],
  },
  {
    id: 'transactions', emoji: '🔎',
    nomeChave: 'agents.transactions', descChave: 'agents.transactions.desc',
    acoesRapidas: [{ id: 'mes_atual', chave: 'quick.tx.month' }],
  },
  {
    id: 'budget', emoji: '📊',
    nomeChave: 'agents.budget', descChave: 'agents.budget.desc',
    acoesRapidas: [{ id: 'situacao', chave: 'quick.budget.status' }],
  },
  {
    id: 'planning', emoji: '🧠',
    nomeChave: 'agents.planning', descChave: 'agents.planning.desc',
    acoesRapidas: [{ id: 'ate_fim_mes', chave: 'quick.planning.month' }],
  },
];

export function acharAgente(id: string): AgenteCard | undefined {
  return AGENTES.find((a) => a.id === id);
}
