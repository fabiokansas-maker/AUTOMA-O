# Entrega para o Claude local — Kansas IA Financeira

Três arquivos de contrato, prontos para portar no app REAL
(`app-financeiro-mobile`, Expo SDK 55 / RN 0.83, Firebase `dinheiro-em-dia-1`).
Nada aqui depende do fonte; tudo aqui é o que a implementação precisa cumprir.

| Arquivo | O que é |
|---|---|
| `agentes.json` | os 6 especialistas + o roteador. Por agente: id, nome, objetivo, prompt de sistema em pt/en/es, ferramentas permitidas (com quais alteram dado e quais exigem confirmação), o que pode ler, o que pode alterar, memória privada/compartilhada, eventos, 3 perguntas de exemplo por idioma e a lista de proibições. |
| `ficha-kansas.json` | título, descrição curta e longa para pt-BR, pt-PT, en-US, en-GB, es-ES e es-419, dentro dos limites da Play (30/80/4000). |
| `roteador-casos.json` | 57 casos reais com o agente esperado, para rodar contra a implementação. |
| `validar.py` | valida os três e mede a linha de base do roteador determinístico. |

```bash
python3 kansas/entrega/validar.py
```

Linha de base medida nesta entrega, só com os sinais determinísticos do
`agentes.json` (sem modelo nenhum):

```
facil   20/20  100.0%
media   21/21  100.0%
dificil 14/16   87.5%
```

Os dois que a regex erra estão documentados de propósito — "Qual meu limite do
cartão?" (limite é do cartão, não do orçamento) e "Quanto eu tenho guardado?"
("guardado" é meta, não saldo). São ambiguidade real de língua: é onde o modelo
entra, depois dos sinais.

## Decisões embutidas nos arquivos

1. **O número nunca vem do modelo.** Toda ferramenta devolve valor calculado;
   o prompt de todo agente proíbe estimar. Dinheiro em centavos inteiros.
2. **Nenhum agente é superusuário.** Planejamento só recebe resumo; está na
   lista de proibições dele ler transação bruta, fatura detalhada e conversa
   alheia.
3. **Toda ferramenta que altera dado exige confirmação** — o validador falha se
   alguém adicionar uma que não exija (exceção declarada: anotar observação).
4. **A ficha não aciona "financial advice".** Os textos falam de organização e
   educação financeira e dizem explicitamente que não há recomendação de
   produto. Se um agente passar a recomendar investimento, a declaração de
   funcionalidades financeiras precisa ser revista por mercado.
5. **O pacote não muda.** `com.pulsefinanceiro.dreai` em todos os arquivos.

## Avisos que vieram do Claude local e que valem para quem mexer aqui

- **`app/` NÃO vai para a Play.** É um esqueleto (sem login, sessão com token
  vazio, versionCode 190) que substituiria o app real e queimaria o
  versionCode. Serve como referência de UI e de tratamento de insets, nada mais.
- **O schema `kansas` no Supabase `cockpit-fabio` não é o backend do app.** Os
  dados dos usuários estão no Firestore. Eu apliquei aquelas migrations antes de
  saber disso; elas ficaram lá, isoladas no schema `kansas`, sem nada ligado.
  Para remover: `drop schema kansas cascade` e apagar a Edge Function
  `kansas-agent`.
- **Nada de keystore ou senha no GitHub** — `AUTOMA-O` é público.
