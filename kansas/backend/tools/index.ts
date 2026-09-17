/**
 * Camada de tools: estreita, validada, sem SQL livre.
 *
 * Nenhuma tool recebe `userId` como argumento. Todas recebem o
 * AgentRequestContext, e é o backend que amarra a consulta ao usuário
 * autenticado. Não existe `queryDatabase(sql)` — de propósito.
 */
import type { AgentRequestContext } from "../context.ts";
import type { FinanceServices } from "./finance.ts";

export type Validator<T> = (raw: unknown) => T;

export interface ToolDefinition<A, R> {
  name: string;
  /** descrição que vai para o modelo — sem nomes de tabela, sem schema */
  description: string;
  /** domínios de dado que a tool toca; conferido contra o registry */
  dataDomains: string[];
  /** true = precisa de confirmação explícita do usuário antes de executar */
  requiresConfirmation: boolean;
  validate: Validator<A>;
  run: (ctx: AgentRequestContext, args: A, svc: FinanceServices) => Promise<R>;
}

/* ------------------------- validadores mínimos ------------------------- */

export const v = {
  obj(raw: unknown): Record<string, unknown> {
    if (raw === null || typeof raw !== "object" || Array.isArray(raw)) {
      throw new ValidationError("esperava um objeto");
    }
    return raw as Record<string, unknown>;
  },
  str(o: Record<string, unknown>, k: string, max = 200): string {
    const x = o[k];
    if (typeof x !== "string" || x.length === 0) {
      throw new ValidationError(`'${k}' precisa ser texto não vazio`);
    }
    if (x.length > max) throw new ValidationError(`'${k}' longo demais`);
    return x;
  },
  optStr(o: Record<string, unknown>, k: string, max = 200): string | undefined {
    return o[k] === undefined || o[k] === null ? undefined : v.str(o, k, max);
  },
  id(o: Record<string, unknown>, k: string): string {
    const x = v.str(o, k, 64);
    if (!/^[A-Za-z0-9_-]{1,64}$/.test(x)) {
      throw new ValidationError(`'${k}' não é um identificador válido`);
    }
    return x;
  },
  int(o: Record<string, unknown>, k: string, min: number, max: number): number {
    const x = Number(o[k]);
    if (!Number.isInteger(x) || x < min || x > max) {
      throw new ValidationError(`'${k}' precisa ser inteiro entre ${min} e ${max}`);
    }
    return x;
  },
  money(o: Record<string, unknown>, k: string): number {
    const x = Number(o[k]);
    if (!Number.isFinite(x) || x < 0 || x > 1e12) {
      throw new ValidationError(`'${k}' não é um valor monetário válido`);
    }
    // centavos inteiros: dinheiro não anda em float solto
    return Math.round(x * 100) / 100;
  },
  isoDate(o: Record<string, unknown>, k: string): string {
    const x = v.str(o, k, 10);
    if (!/^\d{4}-\d{2}-\d{2}$/.test(x)) {
      throw new ValidationError(`'${k}' precisa ser AAAA-MM-DD`);
    }
    return x;
  },
  dateRange(o: Record<string, unknown>): { from: string; to: string } {
    const from = v.isoDate(o, "from");
    const to = v.isoDate(o, "to");
    if (from > to) throw new ValidationError("'from' depois de 'to'");
    const dias = (Date.parse(to) - Date.parse(from)) / 86_400_000;
    // janela limitada: minimiza o que sai do banco e o que chega no modelo
    if (dias > 730) throw new ValidationError("janela máxima de 24 meses");
    return { from, to };
  },
};

export class ValidationError extends Error {
  constructor(msg: string) { super(msg); this.name = "ValidationError"; }
}

/* ----------------------------- as tools ------------------------------- */

export const TOOLS: Record<string, ToolDefinition<never, unknown>> = Object.fromEntries(
  ([
    {
      name: "get_available_balance",
      description: "Saldo disponível hoje e o que já está comprometido nos próximos dias.",
      dataDomains: ["accounts", "balances"],
      requiresConfirmation: false,
      validate: () => ({}),
      run: (ctx, _a, svc) => svc.getAvailableBalance(ctx),
    },
    {
      name: "get_account_balances",
      description: "Saldo por conta do usuário.",
      dataDomains: ["accounts", "balances"],
      requiresConfirmation: false,
      validate: () => ({}),
      run: (ctx, _a, svc) => svc.getAccountBalances(ctx),
    },
    {
      name: "get_upcoming_commitments",
      description: "Compromissos financeiros já assumidos para os próximos N dias.",
      dataDomains: ["cashflow"],
      requiresConfirmation: false,
      validate: (raw) => ({ days: v.int(v.obj(raw ?? {}), "days", 1, 180) }),
      run: (ctx, a, svc) => svc.getUpcomingCommitments(ctx, (a as { days: number }).days),
    },
    {
      name: "get_open_invoices",
      description: "Faturas abertas dos cartões, com fechamento e vencimento.",
      dataDomains: ["cards", "invoices"],
      requiresConfirmation: false,
      validate: () => ({}),
      run: (ctx, _a, svc) => svc.getOpenInvoices(ctx),
    },
    {
      name: "get_invoice_details",
      description: "Detalhe de uma fatura específica do usuário.",
      dataDomains: ["invoices", "invoice_items"],
      requiresConfirmation: false,
      validate: (raw) => ({ invoiceId: v.id(v.obj(raw), "invoiceId") }),
      run: (ctx, a, svc) =>
        svc.getInvoiceDetails(ctx, (a as { invoiceId: string }).invoiceId),
    },
    {
      name: "compare_invoice_to_previous",
      description: "Compara a fatura atual com a do mês anterior por categoria.",
      dataDomains: ["invoices", "invoice_items"],
      requiresConfirmation: false,
      validate: (raw) => ({ invoiceId: v.id(v.obj(raw), "invoiceId") }),
      run: (ctx, a, svc) =>
        svc.compareInvoiceToPrevious(ctx, (a as { invoiceId: string }).invoiceId),
    },
    {
      name: "get_transactions",
      description: "Movimentações do usuário num período, com filtro opcional de categoria.",
      dataDomains: ["transactions"],
      requiresConfirmation: false,
      validate: (raw) => {
        const o = v.obj(raw);
        return { ...v.dateRange(o), category: v.optStr(o, "category", 60) };
      },
      run: (ctx, a, svc) =>
        svc.getTransactions(ctx, a as { from: string; to: string; category?: string }),
    },
    {
      name: "categorize_transaction",
      description: "Troca a categoria de uma movimentação do usuário.",
      dataDomains: ["transactions", "categories"],
      requiresConfirmation: true,
      validate: (raw) => {
        const o = v.obj(raw);
        return { transactionId: v.id(o, "transactionId"), category: v.str(o, "category", 60) };
      },
      run: (ctx, a, svc) =>
        svc.categorizeTransaction(ctx, a as { transactionId: string; category: string }),
    },
    {
      name: "get_goals",
      description: "Metas do usuário e o progresso de cada uma.",
      dataDomains: ["goals"],
      requiresConfirmation: false,
      validate: () => ({}),
      run: (ctx, _a, svc) => svc.getGoals(ctx),
    },
    {
      name: "simulate_goal_scenario",
      description: "Simula quanto falta por mês para bater uma meta numa data.",
      dataDomains: ["goals", "financial_capacity_summary"],
      requiresConfirmation: false,
      validate: (raw) => {
        const o = v.obj(raw);
        return { goalId: v.id(o, "goalId"), targetDate: v.isoDate(o, "targetDate") };
      },
      run: (ctx, a, svc) =>
        svc.simulateGoalScenario(ctx, a as { goalId: string; targetDate: string }),
    },
    {
      name: "get_budget_status",
      description: "Situação do orçamento por categoria no mês corrente.",
      dataDomains: ["budgets", "budget_categories"],
      requiresConfirmation: false,
      validate: () => ({}),
      run: (ctx, _a, svc) => svc.getBudgetStatus(ctx),
    },
    {
      name: "set_budget_limit",
      description: "Define o limite mensal de uma categoria.",
      dataDomains: ["budgets", "budget_categories"],
      requiresConfirmation: true,
      validate: (raw) => {
        const o = v.obj(raw);
        return { category: v.str(o, "category", 60), limit: v.money(o, "limit") };
      },
      run: (ctx, a, svc) =>
        svc.setBudgetLimit(ctx, a as { category: string; limit: number }),
    },
    {
      name: "create_financial_alert",
      description: "Cria um lembrete/alerta financeiro para o usuário.",
      dataDomains: ["alerts"],
      requiresConfirmation: true,
      validate: (raw) => {
        const o = v.obj(raw);
        return { title: v.str(o, "title", 120), when: v.isoDate(o, "when") };
      },
      run: (ctx, a, svc) =>
        svc.createFinancialAlert(ctx, a as { title: string; when: string }),
    },
    {
      name: "get_financial_capacity_summary",
      description: "RESUMO da capacidade financeira mensal. Não devolve transações brutas.",
      dataDomains: ["summaries_only"],
      requiresConfirmation: false,
      validate: () => ({}),
      run: (ctx, _a, svc) => svc.getFinancialCapacitySummary(ctx),
    },
  ] as Array<ToolDefinition<never, unknown>>).map((t) => [t.name, t]),
);

export function toolNamesFor(allowed: string[]): string[] {
  return allowed.filter((n) => n in TOOLS);
}
