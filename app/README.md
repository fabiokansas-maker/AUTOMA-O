# Kansas IA Financeira — app Android

> ## ⛔ NÃO PUBLICAR ESTE APP NA PLAY
>
> Este diretório é **referência**, não o produto. O app real é
> `app-financeiro-mobile` (Expo SDK 55 / RN 0.83, backend Firebase
> `dinheiro-em-dia-1`), que está em produção como vc57 / 1.8.8.
>
> Publicar o que está aqui substituiria o app real — que tem login, importação
> de fatura, assinatura paga e dados no Firestore — por um esqueleto sem
> autenticação, e ainda queimaria o versionCode até 190.
>
> O que aproveitar daqui: o tratamento de edge-to-edge/insets, o renderizador
> de blocos tipados, `money.ts` e a home de especialistas. O contrato dos
> agentes está em `kansas/entrega/`.


Implementação agent-first do app publicado como `com.pulsefinanceiro.dreai`
("Dinheiro em Dia" na loja hoje).

## O que é importante saber antes de mexer

**Esta é uma implementação nova, escrita do zero**, porque o fonte do app atual
está no PC do Fabio e nunca esteve acessível a esta sessão. Ela respeita as
travas que a Play impõe para continuar sendo *o mesmo app*:

| Trava | Aqui |
|---|---|
| `applicationId` | `com.pulsefinanceiro.dreai` — **não mude** |
| assinatura | `signingConfigs.release` lê do ambiente; a upload key nunca entra no repo |
| `targetSdk` | 36 (exigência para qualquer atualização enviada desde 31/08/2026) |
| `versionCode` | 190 — precisa ser maior que o publicado |
| marca visível | `res/values/strings.xml` → "Kansas IA Financeira" |

Quando o fonte original aparecer, o caminho é **mesclar**, não substituir: trazer
para cá os repositories, regras de negócio e integrações que já funcionam, e
ligá-los às tools do backend. A UI antiga é o que sai.

## Estrutura

```
android/                projeto Android: identidade, edge-to-edge, assinatura
  MainActivity.kt       enableEdgeToEdge + setDecorFitsSystemWindows(false)
  values/styles.xml     barras transparentes (claro e escuro)
src/App.tsx             raiz: SafeAreaProvider + navegação hub→agente→ajustes
src/agents/catalog.ts   os 6 especialistas (ids batem com o registry do backend)
src/screens/            hub, agente, ajustes
src/components/         blocos tipados + folha de denúncia de resposta de IA
src/lib/api.ts          única porta para dados; não manda user_id
src/lib/money.ts        Intl por contexto — nunca "R$ " + valor
src/lib/router.ts       escolhe QUEM responde; sem acesso a dado
src/i18n/               pt, en, es — nenhuma string cravada em tela
```

## Rodar as checagens

```bash
cd app
npm ci
npx tsc --noEmit                                   # typecheck
node --experimental-strip-types src/__tests__/run.ts   # 70 testes
cd .. && python3 kansas/tools/audit_app.py app --require-target 36
```

## O que ainda não existe aqui

- **Login.** `App.tsx` monta a sessão com token vazio: o fluxo de autenticação
  do app atual (Firebase, pelo que os registros indicam) entra no lugar.
- **Ícone e splash.** `mipmap/ic_launcher` precisa vir do app original para a
  marca não mudar sozinha na gaveta do aparelho.
- **Nunca rodou em aparelho.** Typecheck e testes passam; instalação, navegação
  real e insets em telefone físico ainda não foram vistos. Primeiro envio deve
  ir para o track **interno**, não para produção.
