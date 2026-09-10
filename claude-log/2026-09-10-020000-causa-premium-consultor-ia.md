---
session: b9a215c3-2fe4-5a92-bf2a-b20226cb7440
agent: claude
ts: 2026-09-10T02:00:00Z
status: blocked
prioridade: CRITICA
tags: [dinheiro-em-dia, premium, gemini, faturamento, preco, causa-raiz]
---

# Causa raiz provável do "paguei e não liberou": Premium = IA, e a IA é paga na conta suspensa

## Fatos novos (extraídos da landing page oficial do próprio app)

`https://dinheiro-em-dia-1.web.app` → **HTTP 200, projeto VIVO** (hosting responde).
Isso derruba a hipótese de "projeto Firebase morto".

Texto literal do site:
> "O Consultor de IA e as análises avançadas ficam no Premium, por **R$ 1,00 por mês**
> — ou **R$ 10,00 no ano**."
> "Controlar gastos, ver para onde foi o dinheiro, organizar as contas por banco e
> criar metas: **tudo no plano gratuito**."

## Consequência lógica

1. O **único** valor do Premium é o **Consultor de IA** (+ análises avançadas).
   Todo o resto do app é gratuito.
2. Consultor de IA ⇒ chamadas à API Gemini.
3. API Gemini ⇒ cobrada na conta de faturamento **017591-F9E0B2-232353**.
4. Essa conta foi **SUSPENSA em 08/09 16:14 BRT**, e no mesmo dia o Google AI Studio
   mandou "your billing account has been moved to a lower tier".
5. A compra do Premium foi às **08/09 22:27 BRT** — **6 horas depois**.

Ou seja: comprou-se acesso a uma IA cuja conta pagadora estava suspensa horas antes.
Para o usuário, "Premium não liberou" e "a IA não responde" são o mesmo sintoma.

## CORREÇÃO de nota anterior

O registro de 09/09 dizia que R$ 1,00/mês parecia "SKU de teste esquecido em
produção". **ERRADO.** É preço deliberado, publicado no site do produto, e bate com
a faixa "R$ 1,00 – R$ 10,00 por item" da ficha do Play. São 2 SKUs: mensal R$ 1,00 e
anual R$ 10,00.

## Agravante econômico (novo)

O Premium entrega uma feature de **custo marginal variável** (cada pergunta ao
Consultor consome token de Gemini, cobrado por uso). A R$ 1,00/mês:
- receita líquida por assinante ≈ R$ 0,85/mês
- um assinante que use o Consultor com frequência pode custar **mais** que isso

Não é apenas "preço baixo": é margem que pode ficar **negativa** com o uso.
Preço de feature de IA precisa de teto de uso (cota) ou preço compatível com o custo
de inferência. Concorrentes cobram R$ 14,99–29,90 na entrada mensal.

## Teste que ficou bloqueado

Tentativa de chamar `generativelanguage.googleapis.com` com a `GEMINI_API_KEY` do
`.env` do Drive (para provar se a IA está fora do ar) foi **bloqueada pelo
classificador de permissão do ambiente**. Não foi contornada. Se liberada, fecha a
prova em uma chamada.

## Bloqueio estrutural que impede CONSERTAR (não só diagnosticar)

O código-fonte do app não está em nenhum lugar acessível a esta sessão (repo,
GitHub, Supabase, Drive — verificado em 05/09). Sem ele não há como corrigir o fluxo
de billing nem a liberação do Premium. Diagnóstico é o teto do que dá para entregar
daqui.

## Ordem correta de ataque

1. Regularizar o faturamento GCP — sem isso o Premium não tem o que entregar.
2. Confirmar no código se o app faz `acknowledgePurchase` e como concede o
   entitlement (teste de estorno de 11/09 ajuda a decidir).
3. Só então revisar preço/cota do Premium.
