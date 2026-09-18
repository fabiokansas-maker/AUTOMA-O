# 2026-09-18 — Telegram removido e o app escrito

## Telegram: fora

O Fabio não usa. Removido de `play_watch.py`, `kansas-watch.yml` e do
bootstrap, nas duas branches. O vigia agora escreve `evidence/play-status.md`
no repositório e o workflow commita. Zero referência a bot sobrou.

Confirmado em execução real no runner (branch default): relatório escrito,
"sem novidade" — ou seja, a correção do cache regional funcionou em produção
(o runner viu "16 de set", não gerou alerta fantasma).

## O app foi escrito

Como o fonte original nunca esteve acessível, `app/` agora tem a implementação
agent-first completa. Travas respeitadas para continuar sendo O MESMO app:
`applicationId com.pulsefinanceiro.dreai`, assinatura vinda do ambiente,
`targetSdk 36`, `versionCode 190`, marca nova só em `strings.xml`.

Verificado nesta sessão:

| Checagem | Resultado |
|---|---|
| `tsc --noEmit` (strict + noUncheckedIndexedAccess) | 0 erros |
| testes do app | 70 verdes |
| `audit_app.py app --require-target 36` | 0 achados, porta aberta |
| CI completo no GitHub | verde |

## Dois bugs reais que as ferramentas pegaram

1. **locale malformado** (`""`, `"pt"`, `"-BR"`) gerava campo `undefined` em
   `money.ts` — quebraria a formatação em aparelho com locale estranho.
   Corrigido no app e no núcleo.
2. **`unicos[0]` sem checagem** no roteador. Mesmo caso, mesmos dois lugares.

## E um defeito do meu próprio auditor

Ele acusava 7 falsos positivos no app novo: contava comentário que ALERTA
sobre `"R$ " + valor` como se fosse o erro, e padding interno de card como
compensação de barra de sistema. Agora ignora comentários, aceita fallback
declarado (`?? 'BRL'`) e só cobra padding em arquivo que não trata insets —
e segue acusando os 3 bloqueantes do app ruim de teste.

## O que falta, sem rodeio

- **Nunca rodou em aparelho.** Typecheck e teste não substituem instalar.
  Primeiro envio: track **interno**.
- **Login**: `App.tsx` monta sessão com token vazio. O fluxo real (Firebase,
  pelos registros do cockpit) entra aí.
- **Ícone/splash**: precisam vir do app original, senão a marca muda sozinha
  na gaveta do aparelho.
- **Publicar**: falta a service account da Play (Google Cloud + acesso no
  Console) e a upload key. Sem elas nenhum AAB sobe, de nenhuma máquina.
