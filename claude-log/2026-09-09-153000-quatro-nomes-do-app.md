---
session: b9a215c3-2fe4-5a92-bf2a-b20226cb7440
agent: claude
ts: 2026-09-09T15:30:00Z
status: completed
tags: [dinheiro-em-dia, play-store, traducao, aso, descoberta]
---

# ACHADO: o app tem 4 nomes diferentes na loja — causa raiz de "ninguém acha"

## Como foi apurado (verificação direta, não suposição)

`curl` na ficha pública do Play para `com.pulsefinanceiro.dreai` variando `hl=`,
e busca real na loja. Tudo HTTP 200, leitura pública, nada alterado.

## Resultado 1 — o app É encontrável (a queixa não procede hoje)

Busca `"Dinheiro em Dia"` em `hl=pt_BR&gl=BR`:
- **posição 1 de 50 resultados**
- concorrente direto homônimo (`br.com.leonardorosario.dinheiroemdia`) fica em 2º

Também aparece com `hl=en_US` e com a query em minúsculas. Está publicado,
indexado e ranqueando em primeiro. **Não existe problema de indexação.**

## Resultado 2 — o app tem QUATRO nomes (esse é o problema real)

| locale | título na loja |
|---|---|
| pt_BR | Dinheiro em Dia |
| en_US | **Budget Planner** |
| en_GB | **Expense Tracker** |
| es_419 | **Control de Gastos** |
| fr_FR / de_DE / it_IT | Dinheiro em Dia (cai no default) |

Dois nomes diferentes **para o mesmo idioma** (en_US vs en_GB). Isso não é
descuido de tradução — é a ficha da loja com o campo *título* localizado.

Outros dados da ficha: dev `FABIOKANSAS`, tag "Compras no app" ativa em ambos os
locales (o app tem monetização no ar; há inclusive recibo de assinatura
`FABIOKANSAS` em 08/09).

## Por que isso mata o produto

1. Boca a boca quebra: indicação por nome falha em qualquer aparelho que não
   esteja em pt-BR.
2. "Budget Planner" / "Expense Tracker" são termos genéricos disputados por
   milhares de apps — o app perde identidade e afunda no ranking desses termos.
3. Usuário que ouviu falar do app e vê outro nome acha que baixou o errado.

## Correção correta

Nome de marca **não se traduz** (ninguém traduz Nubank, iFood, Spotify).
- título = `Dinheiro em Dia` em TODOS os locales
- os termos de busca ("budget planner", "expense tracker", "control de gastos")
  vão para a **descrição curta/completa** de cada idioma — continuam ajudando ASO
  sem trocar o nome do app

## Caminho de automação (para não depender de clique)

A Google Play Developer API **tem** endpoint para isso, ao contrário do status de
verificação de desenvolvedor:
`androidpublisher.edits.listings.update` (title, shortDescription, fullDescription
por `language`), dentro de um ciclo `edits.insert` → `listings.update` → `edits.commit`.

Bloqueio atual: exige service account com acesso ao Play Console do usuário
(GCP + vínculo no Play Console). Não existe no ambiente hoje. **Enquanto não
existir, nenhum agente consegue alterar a ficha.**

## Status honesto

Nada disso foi corrigido. O achado é diagnóstico, feito em 09/09 depois que o
usuário cobrou. Nenhuma alteração foi feita no app nem na ficha.
