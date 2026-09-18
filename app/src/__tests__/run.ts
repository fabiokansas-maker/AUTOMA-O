/**
 * Testes do app que não dependem de renderizar tela:
 * i18n, formatação sensível a país e roteamento da barra de perguntas.
 *
 *   node --experimental-strip-types src/__tests__/run.ts
 */
import assert from 'node:assert/strict';
import { traduzir, idiomasDisponiveis } from '../i18n/index.ts';
import { formatMoney, formatDate, resolveLocaleContext } from '../lib/money.ts';
import { routeBySignals } from '../lib/router.ts';
import { AGENTES, acharAgente } from '../agents/catalog.ts';

let n = 0;
const ok = (c: boolean, m: string) => { assert.ok(c, m); n++; console.log('PASS ', m); };

/* ------------------------------- i18n ------------------------------- */
ok(traduzir('pt', 'home.greeting', { name: 'Fabio' }) === 'Olá, Fabio',
   'interpolação de nome em pt');
ok(traduzir('en', 'home.greeting', { name: 'Fabio' }) === 'Hi, Fabio',
   'interpolação de nome em en');
ok(traduzir('es', 'home.greeting', { name: 'Ana' }).startsWith('Hola'),
   'espanhol tem saudação própria');
ok(traduzir('de', 'agent.send') === traduzir('en', 'agent.send'),
   'idioma sem dicionário cai no inglês, não quebra');
ok(traduzir('pt', 'chave.que.nao.existe') === 'chave.que.nao.existe',
   'chave inexistente devolve a própria chave em vez de quebrar');
ok(!traduzir('pt', 'settings.delete_warning').includes('{'),
   'aviso de exclusão não tem placeholder solto');

// nenhuma tela pode ficar sem texto num idioma que o app oferece
for (const idioma of idiomasDisponiveis()) {
  for (const a of AGENTES) {
    ok(traduzir(idioma, a.nomeChave) !== a.nomeChave,
       `agente ${a.id} tem nome em ${idioma}`);
    for (const q of a.acoesRapidas) {
      ok(traduzir(idioma, q.chave) !== q.chave,
         `ação rápida ${q.id} traduzida em ${idioma}`);
    }
  }
}

/* --------------------------- dinheiro e data ------------------------ */
const br = { locale: 'pt-BR', timezone: 'America/Sao_Paulo' };
const us = { locale: 'en-US', timezone: 'America/New_York' };
ok(formatMoney({ cents: 384277, currency: 'BRL' }, br).includes('3.842,77'),
   'BRL em pt-BR');
ok(formatMoney({ cents: 384277, currency: 'USD' }, us).includes('3,842.77'),
   'USD em en-US');
ok(formatMoney({ cents: 500, currency: 'JPY' }, { locale: 'ja-JP' }).includes('500'),
   'JPY não apanha divisão por 100');
ok(!formatMoney({ cents: 100, currency: 'EUR' }, br).startsWith('R$'),
   'moeda do dado manda, não o país do app');
ok(formatDate('2026-09-25', br).length > 0, 'data formatada pelo locale');

// locale malformado vindo do aparelho não pode derrubar o app
for (const ruim of ['', 'pt', '-BR', 'xx-YY']) {
  const ctx = resolveLocaleContext(ruim);
  ok(!!ctx.language && !!ctx.currency && !!ctx.locale,
     `locale ${JSON.stringify(ruim)} não gera campo vazio`);
  ok(formatMoney({ cents: 1, currency: ctx.currency }, ctx).length > 0,
     `formatação sobrevive ao locale ${JSON.stringify(ruim)}`);
}
ok(resolveLocaleContext('en-US', { currency: 'BRL' }).currency === 'BRL',
   'escolha do usuário vence o padrão do aparelho');

/* ------------------------------ roteamento -------------------------- */
ok(routeBySignals('por que minha fatura veio tão alta?')?.primaryAgent === 'invoices',
   'fatura -> agente de faturas');
ok(routeBySignals('quanto tenho disponível hoje?')?.primaryAgent === 'balance',
   'saldo -> agente de saldo');
const cruzada = routeBySignals('quanto posso gastar sem comprometer minha meta?');
ok(cruzada?.primaryAgent === 'planning' && cruzada.supportingAgents.length > 0,
   'pergunta cruzada -> planejamento com resumos');
ok(routeBySignals('oi') === null, 'sem sinal, o roteador não chuta');

/* ------------------------------ catálogo ---------------------------- */
ok(AGENTES.length === 6, 'seis especialistas na home');
ok(new Set(AGENTES.map((a) => a.id)).size === 6, 'sem id repetido');
ok(acharAgente('invoices')?.emoji === '💳', 'lookup por id funciona');
ok(acharAgente('superagente') === undefined, 'agente inexistente não aparece');

console.log(`\nRESULTADO: VERDE — ${n} testes do app passaram.`);
