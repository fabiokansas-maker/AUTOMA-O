/**
 * Cálculo financeiro NÃO passa pelo LLM.
 *
 * Toda soma de fatura, saldo, data de fechamento, limite e projeção sai
 * daqui — código determinístico, testável, com o mesmo resultado sempre.
 * O modelo recebe o objeto pronto e faz o que ele faz bem: explicar.
 *
 * Este arquivo é a INTERFACE. A implementação concreta deve envolver os
 * repositories que o app JÁ tem (é reaproveitamento, não reescrita):
 *
 *     InvoiceScreen              InvoiceAgent
 *          |                          |
 *     InvoiceRepository   <──────  getOpenInvoices tool
 *          |                          |
 *     Firestore/API               mesma fonte, mesma regra
 */
import type { AgentRequestContext } from "../context.ts";

/** Dinheiro nunca é number solto: valor + moeda andam juntos. */
export interface Money {
  /** em centavos, inteiro — sem erro de ponto flutuante */
  readonly cents: number;
  readonly currency: string;
}

export const money = (cents: number, currency: string): Money =>
  Object.freeze({ cents: Math.round(cents), currency });

export const sum = (values: Money[], currency: string): Money => {
  for (const m of values) {
    if (m.currency !== currency) {
      throw new Error(`mistura de moedas: ${m.currency} em total ${currency}`);
    }
  }
  return money(values.reduce((a, m) => a + m.cents, 0), currency);
};

export interface BalanceSummary {
  available: Money;
  committedNext7Days: Money;
  reallyFree: Money;
  asOf: string;
}

export interface InvoiceSummary {
  invoiceId: string;
  cardLabel: string;
  /** SEMPRE mascarado: nunca o número completo, nem em log */
  cardLast4: string;
  total: Money;
  closingDate: string;
  dueDate: string;
  status: "open" | "closed" | "paid";
}

export interface FinanceServices {
  getAvailableBalance(ctx: AgentRequestContext): Promise<BalanceSummary>;
  getAccountBalances(ctx: AgentRequestContext): Promise<Array<{ accountId: string; label: string; balance: Money }>>;
  getUpcomingCommitments(ctx: AgentRequestContext, days: number): Promise<{ total: Money; items: Array<{ label: string; amount: Money; date: string }> }>;
  getOpenInvoices(ctx: AgentRequestContext): Promise<InvoiceSummary[]>;
  getInvoiceDetails(ctx: AgentRequestContext, invoiceId: string): Promise<InvoiceSummary & { topCategories: Array<{ category: string; amount: Money }> }>;
  compareInvoiceToPrevious(ctx: AgentRequestContext, invoiceId: string): Promise<{ current: Money; previous: Money; deltaPct: number; drivers: Array<{ category: string; delta: Money }> }>;
  getTransactions(ctx: AgentRequestContext, a: { from: string; to: string; category?: string }): Promise<Array<{ id: string; date: string; label: string; amount: Money; category: string }>>;
  categorizeTransaction(ctx: AgentRequestContext, a: { transactionId: string; category: string }): Promise<{ ok: true }>;
  getGoals(ctx: AgentRequestContext): Promise<Array<{ id: string; label: string; target: Money; saved: Money; progressPct: number }>>;
  simulateGoalScenario(ctx: AgentRequestContext, a: { goalId: string; targetDate: string }): Promise<{ requiredMonthly: Money; monthsLeft: number; feasible: boolean }>;
  getBudgetStatus(ctx: AgentRequestContext): Promise<Array<{ category: string; limit: Money; spent: Money; remaining: Money; pace: "ok" | "atencao" | "estourado" }>>;
  setBudgetLimit(ctx: AgentRequestContext, a: { category: string; limit: number }): Promise<{ ok: true }>;
  createFinancialAlert(ctx: AgentRequestContext, a: { title: string; when: string }): Promise<{ alertId: string }>;
  /** RESUMO — é isto, e só isto, que o Agente de Planejamento enxerga. */
  getFinancialCapacitySummary(ctx: AgentRequestContext): Promise<{ monthlyIncome: Money; committed: Money; discretionary: Money; salaryDay: number }>;
}

/* ---------------- regras determinísticas reaproveitáveis ---------------- */

/** Quanto sobra de verdade: disponível menos o que já tem dono. */
export function reallyFree(available: Money, committed: Money): Money {
  if (available.currency !== committed.currency) {
    throw new Error("moedas diferentes em reallyFree");
  }
  return money(available.cents - committed.cents, available.currency);
}

/** Aporte mensal necessário. Nada de LLM estimando conta de chegar. */
export function requiredMonthlyContribution(
  target: Money, saved: Money, monthsLeft: number,
): Money {
  if (target.currency !== saved.currency) throw new Error("moedas diferentes");
  if (monthsLeft <= 0) return money(Math.max(0, target.cents - saved.cents), target.currency);
  return money(Math.max(0, Math.ceil((target.cents - saved.cents) / monthsLeft)), target.currency);
}

/** Ritmo de gasto contra o limite, considerando o dia do mês. */
export function budgetPace(
  spent: Money, limit: Money, dayOfMonth: number, daysInMonth: number,
): "ok" | "atencao" | "estourado" {
  if (limit.cents <= 0) return "ok";
  if (spent.cents > limit.cents) return "estourado";
  const esperado = limit.cents * (dayOfMonth / daysInMonth);
  return spent.cents > esperado * 1.15 ? "atencao" : "ok";
}
