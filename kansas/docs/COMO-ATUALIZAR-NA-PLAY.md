# O que falta para o app ser atualizado na Play

Resposta curta: **quatro portas.** Duas são regra do Google, uma é mecânica de
build, e uma é a única que depende de alguém olhar uma tela.

## Porta 1 — `targetSdk` ≥ 36 (regra do Google, já em vigor)

Desde **31/08/2026**, toda atualização enviada à Play precisa mirar **Android 16
(API 36)**. App existente precisa de pelo menos API 35 para continuar aparecendo
a novos usuários em Android recente. Dá para pedir prorrogação até 01/11/2026.

**Estado: desconhecido.** O fonte do app não está aqui, e nem a página da loja
nem os mirrors de APK (410/403) expõem o target. Quem responde em 5 segundos:

```bash
python3 kansas/tools/audit_app.py <pasta-do-app> --require-target 36
# PORTA FECHADA: targetSdk=34 < 36. A Play recusa o upload.
# PORTA ABERTA:  targetSdk=36 atende o mínimo 36.
```

Se estiver abaixo: subir o target liga o **edge-to-edge** do Android 15+, e é aí
que menu e botão vão parar debaixo das barras. Por isso `kansas/app/` já vem com
insets resolvidos — a correção anda junto com o upgrade, não depois dele.

## Porta 2 — verificação de desenvolvedor Android (vence **30/09/2026**)

E-mail do Google Play de 04/09/2026, "último lembrete": todo app precisa estar
registrado até 30/09, senão *"serão removidos da plataforma no mundo todo"*.
Mais de 99% foram registrados automaticamente (quem usa a chave de assinatura do
Google Play). O status aparece ao lado de cada app na home do Play Console, com
filtro para "não registrados".

**É a única coisa desta lista que nenhuma API responde.** É olhar, não fazer.

## Porta 3 — o build não pode depender do seu PC

Hoje ele depende: o fonte está em `C:\Dev`, junto com a keystore e o Android
SDK. Se a máquina não liga, não sai atualização. Já está no repositório o
caminho que tira isso da sua mão de vez:

`.github/workflows/kansas-release.yml` — gera o AAB assinado e envia para a Play
sozinho. Ele **se recusa a publicar errado**: confere `targetSdk` antes de
compilar, confere que o `applicationId` continua `com.pulsefinanceiro.dreai`
(trocar isso faria a Play tratar como outro app e os usuários atuais parariam de
atualizar), e em produção sobe com rollout de 5%, nunca 100% de cara.

Para ele rodar, faltam, uma vez só:

| O que | Por que só você consegue |
|---|---|
| fonte do app dentro deste repo (ou repo próprio que eu possa anexar) | está no seu PC |
| `ANDROID_KEYSTORE_BASE64` + senha/alias | a upload key é sua; sem ela a Play rejeita o AAB |
| `PLAY_SERVICE_ACCOUNT_JSON` | conta de serviço criada no Google Cloud + acesso dado no Play Console |

Com isso, atualizar vira um push. Sem isso, continua sendo você compilando na mão.

## Porta 4 — versionCode maior que o publicado

A Play recusa AAB com `versionCode` menor ou igual ao que já está lá. Também dá
para responder sem abrir o Console:

```bash
export PLAY_SERVICE_ACCOUNT_JSON=/caminho/chave.json
python3 kansas/tools/play_status.py com.pulsefinanceiro.dreai
# lista faixa por faixa, status e versionCode, e diz qual deve ser o próximo
```

Ele abre um *edit* na API, lê e descarta — não publica nada.

## O que já está confirmado e não bloqueia

- A ficha está no ar e foi atualizada em **17/09/2026** (v1.8.8), com
  **"Compras no app"** ativo — o produto de assinatura que estava pendente em
  junho já existe.
- Downloads ainda em **10+**: o gargalo de crescimento é distribuição, não
  publicação.
- Renomear para **Kansas IA Financeira** é seguro e não mexe em nada disso —
  título público muda, `applicationId` não.
