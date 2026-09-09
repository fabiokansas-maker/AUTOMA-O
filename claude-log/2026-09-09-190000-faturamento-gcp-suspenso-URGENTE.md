---
session: b9a215c3-2fe4-5a92-bf2a-b20226cb7440
agent: claude
ts: 2026-09-09T19:00:00Z
status: blocked
prioridade: CRITICA
tags: [dinheiro-em-dia, gcp, faturamento, firebase, assinatura, urgente]
---

# URGENTE: conta de faturamento do GCP suspensa — prazo ~08/10 para o app morrer

## O fato

E-mail `CloudPlatform-noreply@google.com`, **2026-09-08 19:14**, thread `1a0827131c090fbf`:

> "Sua conta de faturamento **017591-F9E0B2-232353** foi suspensa por falta de
> pagamento (...) você poderá perder o acesso aos seus projetos e os serviços
> poderão deixar de funcionar (...) **caso não forneça um instrumento de pagamento
> válido dentro de 30 dias, sua conta de faturamento e os projetos relacionados
> serão encerrados**."

30 dias a partir de 08/09 → **encerramento por volta de 08/10/2026**.

## PROVA de que essa conta é a do app (não é suposição)

Incidente de abril, mesma conta de faturamento:
- **08/04** — `017591-F9E0B2-232353` suspensa; **no mesmo dia** os 3 projetos caem:
  - `dinheiro-em-dia-1` (**Dinheiro em Dia**)
  - `silicon-cell-458502-c8` (My First Project)
  - `gen-lang-client-0415018805` (FINANCE)
- **11/04** — conta volta a "situação regular" e os **3 projetos são reinstaurados juntos**
- **11/04** — Firebase: "Fizemos upgrade do projeto Dinheiro em Dia devido às suas
  atividades no Google Cloud — um usuário definiu uma nova conta de faturamento"

Logo: **`dinheiro-em-dia-1` está vinculado a `017591-F9E0B2-232353`.** Se essa conta
for encerrada, o Firebase do app vai junto.

## Escalada atual (já vinha avisando)

| data | evento |
|---|---|
| 15/03 | 1º aviso "vencida ou informações de pagamento inválidas" |
| 01/09 | "projeto FINANCE corre o risco de ser suspenso" |
| 04/09 | "projeto My First Project corre o risco de ser suspenso" |
| **08/09** | **conta de faturamento SUSPENSA** |
| 08/09 | Google AI Studio: "billing account moved to a lower tier" (consequência) |
| ~08/10 | encerramento de conta + projetos |

## Causa provável: o cartão do GCP não é o mesmo que funciona no Play

- Play, **08/09 22:27** — compra de `Premium (Dinheiro em Dia)` **R$ 1,00/mês** no
  cartão **Visa-1797** → **aprovada** (pedido GPA.3379-5833-2619-47349)
- GCP, mesmo dia → suspensa por pagamento inválido

Ou seja, existe cartão vivo (Visa-1797); o cadastrado no faturamento do Cloud é outro
e está morto. Padrão bate com falhas em cascata na conta: Google One suspenso (19/07,
02/08), HBO Max recusado (03/09), Tinder recusado 5× desde 27/07.

## Sobre a assinatura do app (o que o usuário perguntou)

**Funciona.** Fluxo de compra validado de ponta a ponta em 08/09.
Ponto de atenção: preço **R$ 1,00/mês** tem cara de SKU de teste em produção.
Alterável por API: `androidpublisher.monetization.subscriptions` (não é web-only).

**A memória do repo NÃO tinha nada sobre problema de assinatura** — verificado em
todas as branches e no `claude-log/`. Se houve trabalho anterior nisso, foi fora
daqui e não deixou registro.

## O que trava a automação

Cadastrar meio de pagamento válido é ação exclusiva do titular do cartão — não há
API para isso e nenhum agente pode fazer. É da mesma classe de
`HOSTINGER_API_TOKEN` no CLAUDE.md: exceção legítima.

O que É automatizável e deve ser feito assim que houver credencial:
- preço/SKU da assinatura via `monetization.subscriptions`
- títulos da ficha por idioma via `edits.listings` (ver nota dos 4 nomes, 09/09)

## Aviso para outros agentes

Se o app "parar de funcionar" nas próximas semanas, **olhe primeiro o faturamento
do GCP**, não o código. O código não vai ter mudado.
