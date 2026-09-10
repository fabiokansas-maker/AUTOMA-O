---
session: b9a215c3-2fe4-5a92-bf2a-b20226cb7440
agent: claude
ts: 2026-09-10T01:30:00Z
status: blocked
prioridade: CRITICA
tags: [dinheiro-em-dia, billing, assinatura, premium, preco, receita]
---

# CRÍTICO: usuário paga a assinatura e o Premium NÃO libera

## O fato relatado e confirmado por recibo

Compra real em **08/09/2026 22:27 BRT**, pedido `GPA.3379-5833-2619-47349`,
`Premium (Dinheiro em Dia)` R$ 1,00/mês, Visa-1797, **aprovada**.
**O Premium não foi liberado no app.**

Cobrança (Google) e liberação (app) são sistemas separados. A cobrança funciona.
A liberação está quebrada. **Todo assinante novo hoje paga e não recebe nada.**

## Duas hipóteses, com teste que as separa

**A — falta `acknowledgePurchase`.** O Play Billing exige confirmação em até 3 dias;
sem ela o Google **estorna automaticamente e revoga**. Sintoma idêntico ao relatado.

**B — backend morto no momento da compra.** Timeline:
- 08/09 **16:14 BRT** — conta de faturamento GCP `017591-F9E0B2-232353` suspensa
- 08/09 **22:27 BRT** — compra efetuada, **6 h depois**

Se a validação da assinatura passa por Firebase/Cloud Functions do projeto
`dinheiro-em-dia-1` (que está nessa conta suspensa), a validação falhou.

**TESTE DECISIVO (sem código, sem ação do usuário):** o prazo de 3 dias vence em
**11/09/2026 ~22:27 BRT**. Verificado em 10/09: **nenhum e-mail de estorno até agora**.
- chegou estorno até 12/09 → **hipótese A confirmada** (falta acknowledge)
- não chegou → acknowledge OK; problema é B ou lógica de entitlement

Rotina `trig_0121WfEMD5xih2anM5KpZRRM` foi instruída a vigiar isso.

## Risco de política (mais grave que o resto)

- Hipótese A: estorno em 3 dias por assinante → receita zero + taxa de estorno alta,
  que o Google monitora e sanciona.
- Hipótese B: cobra recorrente e nunca entrega → reembolsos manuais, review 1★,
  denúncia. **Cobrar sem entregar viola política do Play e derruba app.**

Enquanto não consertar, cada assinante novo é passivo, não receita.

## Análise de preço (dados da própria página do Play, 10/09)

| App | Faixa de compras no app |
|---|---|
| **Dinheiro em Dia** | **R$ 1,00 – R$ 10,00** |
| concorrente | R$ 0,90 – R$ 499,90 |
| concorrente | R$ 1,99 – R$ 399,90 |
| concorrente | R$ 14,99 – R$ 179,90 |
| concorrente | R$ 22,90 – R$ 649,90 |
| concorrente | R$ 29,90 – R$ 289,99 |

Teto mais baixo do mercado (R$ 10 contra R$ 180–650). App **sem anúncios** — ou seja,
assinatura é a única receita.

Matemática (comissão Play 15% no 1º US$ 1M/ano → líquido R$ 0,85 por assinante):
- meta R$ 1.000/mês a R$ 1,00 → **1.176 assinantes**
- meta R$ 1.000/mês a R$ 14,90 → **79 assinantes** (15× menos)

**Vazamento permanente:** no Play, aumento de preço para assinante existente exige
consentimento. Quem assina a R$ 1,00 tende a ficar a R$ 1,00 para sempre (ou cancela
no aumento). Cada dia com R$ 1,00 no ar cria assinante barato **definitivo**.

Faixa lógica pelo mercado: **R$ 9,90 – R$ 14,90/mês** + plano anual com desconto.
Alterável por API: `androidpublisher.monetization.subscriptions` (não é web-only).

## Ordem de ataque recomendada

1. Consertar a liberação do Premium (sem isso, preço é irrelevante).
2. Só depois corrigir o preço — subir preço com entrega quebrada multiplica denúncia.
3. Faturamento GCP (pode ser a causa raiz de 1).
