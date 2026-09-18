# Pierre vs. Kansas — análise com dados, não com opinião

Feita em 18/09/2026 com a ficha pública da Play, 495 avaliações únicas
coletadas (todas as ordenações) e as 24 capturas de tela da loja. O APK do
Pierre não está em nenhum mirror acessível daqui (410/403), então a leitura da
interface veio das capturas oficiais.

## Os números, lado a lado

| | **Pierre: IA financeira pessoal** | **Dinheiro em Dia (seu)** |
|---|---|---|
| Empresa | CloudWalk (dona da InfinitePay) | você |
| Instalações | **1.000.000+** | **10+** |
| Nota | **4,76** com 15.080 avaliações | sem avaliações |
| Distribuição | 13.523×5★ · 684×4★ · 218×3★ · 118×2★ · 535×1★ | — |
| Atualizado | 14/09/2026 | 17/09/2026 |
| Monetização | grátis com assinatura (~R$40/mês, 7 dias de teste) | IAP ativo, sem base |
| Dados | Open Finance, 100+ instituições | nenhuma conexão |

## A notícia ruim: o Pierre já é o app que você me pediu

O briefing que você mandou descreve agentes especializados, conversa com
componentes financeiros dentro, feedback na resposta. As capturas oficiais do
Pierre mostram exatamente isso, já em produção:

- agentes com nome e personagem próprio ("Megamen — seu escudo contra gastos
  fora de controle"), com chave **Ativo/Inativo** e botão **Editar agente**;
- 👍 👎 na resposta do agente — o mesmo mecanismo que o Play exige e que
  implementamos;
- home com cartões de saldo, gastos por categoria e a barra
  **"Pergunte ao Pierre"** — o mesmo roteador de perguntas;
- "Conexões · Cartão · Investimentos" como abas do topo.

Descrição deles, na íntegra: *"agentes de IA criados para acompanhar diferentes
partes da sua vida: percebem padrões, mostram o que merece sua atenção"*.

Competir de frente com isso é perder: eles têm um milhão de instalações, Open
Finance funcionando, cartão próprio e CDB a 111% do CDI para segurar o usuário.

## A notícia boa: as 136 avaliações negativas dizem onde eles falham

Contagem por tema nas notas 1-2★ (136 avaliações):

| Tema | Frequência |
|---|---|
| assinatura / preço / cobrança | **21,3%** |
| conexão bancária / Open Finance falha | **20,6%** |
| trava / crash / lentidão | **19,1%** |
| cartão / limite / crédito | 13,2% |
| privacidade / permissões | 8,8% |
| login / PIN / verificação | 5,9% |
| dado errado (fatura/saldo/parcelas) | 5,9% |
| suporte ausente | 5,9% |

E o que as pessoas escrevem, textualmente:

> **1★ · 26 acharam útil** — "muito fraquinho, os agentes e a IA filtram tudo
> errado, criam gastos que não existem ou não incluem os que existem, não dá
> para confiar nada nela, **e a interface do app é praticamente dependente
> dela, porque não consigo criar nada lá**... é tudo generalista"

> **2★ · 22 acharam útil** — "Não vale o preço, **40 reais por mês**. Ele é
> totalmente focado em IA, de forma que a visão de gráficos fica em segundo
> plano... **a IA é a mesma coisa de puxar um resumo das suas contas e colocar
> no ChatGPT**"

> **1★ · 17 acharam útil** — "alguns custos mensais das minhas faturas são
> divididos entre três, mesmo dando instruções e treinando, o Pierre não
> consegue lidar com esse nível de complexidade... **tem memória subscrita**"

> **1★ · 13 acharam útil** — "**é um app individual, não é possível
> compartilhar dados de contas bancárias de pessoas diferentes** e acessar em
> celulares distintos"

> **1★ · 21 acharam útil** — "Parece que lançaram o produto antes de ficar
> pronto, a IA do chat não conecta com o Vision, traz informações divergentes,
> **erra os valores das faturas em aberto**"

## As quatro brechas reais

1. **Preço.** R$40/mês é o problema nº 1 deles, e o público do seu pitch
   ("quanto sobra até o próximo pagamento") é exatamente quem não paga isso.
2. **Confiança no número.** "Cria gastos que não existem", "erra o valor da
   fatura". O núcleo que construímos força cálculo determinístico fora do LLM —
   o modelo só explica um número que o código calculou. É defensável e é
   exatamente a dor deles.
3. **Nem tudo é chat.** "Não consigo criar nada lá, a interface é dependente da
   IA." Foi o ponto que o próprio briefing levantou e o Pierre errou.
4. **Conta compartilhada.** Duas reclamações independentes entre as mais
   votadas: dividir despesa entre pessoas e acessar em celulares distintos.
   Pierre é individual por desenho. Casal/família/república é um nicho aberto.

## Veredito honesto sobre "alguém pagaria"

**Pelo que existe hoje no seu app, não.** Não por ser feio: porque um app
financeiro sem dado financeiro não entrega nada. Falta login e falta a conexão
que alimenta os agentes — sem isso, o especialista mais bem arquitetado do
mundo responde "não tenho acesso a esse dado".

**O que tem chance de ser pago**, na ordem em que eu faria:

1. ligar dados reais (Open Finance via agregador, ou importação de extrato +
   lançamento manual rápido, que é mais barato e não depende de aprovação);
2. atacar as duas brechas que o Pierre deixou aberto e que ninguém cobre bem:
   **confiabilidade do número** e **gasto compartilhado**;
3. preço abaixo da faixa deles, mirando quem acha R$40 caro;
4. só então gastar energia com marca, ficha e rollout.

Com 10+ instalações, o gargalo hoje não é produto nem arquitetura: é não ter
um único usuário com dado dentro. Enquanto isso não muda, qualquer comparação
de recurso com o Pierre é abstrata.
