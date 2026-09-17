/**
 * Testes do que NÃO pode depender do LLM: cálculo financeiro, validação de
 * argumentos de tool, roteamento e sanitização dos blocos de UI.
 *
 *   node --experimental-strip-types kansas/backend/tests/unit.test.ts
 */
import assert from "node:assert/strict";
import {
  budgetPace, money, reallyFree, requiredMonthlyContribution, sum,
} from "../tools/finance.ts";
import { TOOLS, v, ValidationError } from "../tools/index.ts";
import { routeBySignals } from "../router.ts";
import { sanitizarBlocos } from "../blocks.ts";
import { formatMoney, formatDate, resolveLocaleContext } from "../../app/money.ts";

let pass = 0;
const ok = (cond: boolean, msg: string) => { assert.ok(cond, msg); pass++; console.log("PASS ", msg); };
const explode = (fn: () => unknown, msg: string) => {
  let deu = false;
  try { fn(); } catch { deu = true; }
  assert.ok(deu, msg); pass++; console.log("PASS ", msg);
};

/* ----------------------- dinheiro determinístico ---------------------- */
ok(sum([money(1099, "BRL"), money(201, "BRL")], "BRL").cents === 1300,
   "soma em centavos não acumula erro de float");
explode(() => sum([money(100, "BRL"), money(100, "USD")], "BRL"),
   "somar moedas diferentes é erro, não arredondamento");
ok(reallyFree(money(384277, "BRL"), money(121040, "BRL")).cents === 263237,
   "sobra real = disponível menos comprometido");
ok(requiredMonthlyContribution(money(1000000, "BRL"), money(250000, "BRL"), 15).cents === 50000,
   "aporte mensal necessário é conta de código, não do modelo");
ok(requiredMonthlyContribution(money(1000, "BRL"), money(9999, "BRL"), 3).cents === 0,
   "meta já batida não gera aporte negativo");
ok(budgetPace(money(9000, "BRL"), money(10000, "BRL"), 5, 30) === "atencao",
   "gasto de 90% no dia 5 acende atenção");
ok(budgetPace(money(1500, "BRL"), money(10000, "BRL"), 5, 30) === "ok",
   "gasto proporcional ao dia do mês fica ok");
ok(budgetPace(money(11000, "BRL"), money(10000, "BRL"), 28, 30) === "estourado",
   "acima do limite é estouro");

/* -------------------------- validação de tools ------------------------ */
explode(() => TOOLS.get_transactions.validate({ from: "2026-01-01", to: "2020-01-01" } as never),
   "intervalo invertido é rejeitado");
explode(() => TOOLS.get_transactions.validate({ from: "2020-01-01", to: "2026-01-01" } as never),
   "janela maior que 24 meses é rejeitada (minimiza dado no modelo)");
explode(() => TOOLS.get_invoice_details.validate({ invoiceId: "1; drop table x" } as never),
   "id com injeção é rejeitado antes de chegar no banco");
explode(() => TOOLS.set_budget_limit.validate({ category: "lazer", limit: -5 } as never),
   "limite negativo é rejeitado");
ok(TOOLS.set_budget_limit.requiresConfirmation === true,
   "operação que escreve pede confirmação do usuário");
ok(TOOLS.get_open_invoices.requiresConfirmation === false,
   "leitura não interrompe o usuário com confirmação");
ok(!("queryDatabase" in TOOLS) && !("runSql" in TOOLS),
   "não existe tool de SQL livre no catálogo");
explode(() => v.str({}, "x"), "validador rejeita campo obrigatório ausente");

/* ------------------------------ roteamento ---------------------------- */
ok(routeBySignals("por que minha fatura veio tão alta?")?.primaryAgent === "invoices",
   "pergunta de fatura vai para o Agente de Faturas");
ok(routeBySignals("quanto eu tenho disponível hoje?")?.primaryAgent === "balance",
   "pergunta de saldo vai para o Agente de Saldo");
const cruzada = routeBySignals("quanto posso gastar sem comprometer minha meta?");
ok(cruzada?.primaryAgent === "planning" && cruzada.supportingAgents.length > 0,
   "pergunta que atravessa domínios cai no Planejamento com resumos");
ok(routeBySignals("oi") === null, "sem sinal claro, o roteador não chuta");

/* ---------------------------- blocos de UI ---------------------------- */
ok(sanitizarBlocos([{ type: "money_summary", cents: 1 } as never]).length === 1,
   "bloco do catálogo passa");
ok(sanitizarBlocos([{ type: "<script>", text: "x" } as never])[0].type === "text",
   "bloco fora do catálogo é rebaixado para texto");
ok(sanitizarBlocos(new Array(30).fill({ type: "text", text: "a" }) as never).length === 12,
   "resposta não despeja 30 blocos na tela");

/* ------------------------- moeda e internacionalização ---------------- */
const br = { locale: "pt-BR", timezone: "America/Sao_Paulo" };
const us = { locale: "en-US", timezone: "America/New_York" };
ok(formatMoney({ cents: 123456, currency: "BRL" }, br).includes("1.234,56"),
   "BRL em pt-BR sai 1.234,56");
ok(formatMoney({ cents: 123456, currency: "USD" }, us).includes("1,234.56"),
   "USD em en-US sai 1,234.56");
ok(formatMoney({ cents: 1234, currency: "JPY" }, { locale: "ja-JP" }).includes("1,234"),
   "JPY não tem centavo e não é dividido por 100");
ok(!formatMoney({ cents: 100, currency: "USD" }, br).startsWith("R$"),
   "moeda do dado manda, não o país do app");
ok(formatDate("2026-09-25", br) !== "2026-09-25", "data é formatada pelo locale");
ok(resolveLocaleContext("en-US").currency === "USD",
   "contexto derivado do device escolhe a moeda do país");
ok(resolveLocaleContext("en-US", { currency: "BRL" }).currency === "BRL",
   "escolha salva pelo usuário vence o padrão do device");

console.log(`\nRESULTADO: VERDE — ${pass} testes unitários passaram.`);
