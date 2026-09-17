# Tirar o build do seu PC — o que roda onde

Hoje o app só é atualizado se a sua máquina estiver ligada: o fonte, a keystore
e o Android SDK estão nela. Isso acabou aqui.

```
ANTES                                DEPOIS
┌──────────────┐                     ┌──────────────┐
│  seu PC      │                     │  seu PC      │  ← pode ficar desligado
│  fonte       │                     └──────┬───────┘
│  keystore    │                            │ UMA vez: bootstrap
│  SDK         │                            ▼
│  build       │                     ┌──────────────────────────┐
│  upload      │                     │ repo PRIVADO kansas-app  │
└──────────────┘                     │  fonte (cópia limpa)     │
   tudo depende                      │  secrets de assinatura   │
   de você                           └──────┬───────────────────┘
                                            ▼
                                     ┌──────────────────────────┐
                                     │ GitHub Actions           │
                                     │  kansas-release: AAB →   │
                                     │    Play (rollout 5%)     │
                                     │  kansas-watch: 2×/dia →  │
                                     │    Telegram              │
                                     └──────────────────────────┘
```

## 1. O vigia já roda sem você — nada a fazer

`.github/workflows/kansas-watch.yml`, cron **08h e 19h BRT**, no runner do
GitHub. Cada execução:

- lê a ficha pública da Play (versão, data de atualização, downloads, IAP);
- compara com o estado anterior, que ele mesmo commita em
  `evidence/play-state.json`;
- conta os dias até os prazos do Google que podem tirar o app do ar;
- lê as faixas pela Developer API **se** o secret existir;
- fala no Telegram **só** quando muda algo ou quando um prazo bate num marco
  (30, 14, 7, 5, 3, 2, 1, 0 dias).

Esse estrangulador é de propósito: sem ele, um prazo de 13 dias viraria 26
mensagens. Rodando agora, a saída real é:

```
📱 Dinheiro em Dia
versão 1.8.8 · atualizado 17 de set. de 2026 · 10+ downloads
compras no app: ativas
🚨 verificação de desenvolvedor Android: faltam 13 dia(s) (30/09/2026)
⏳ prorrogação do target SDK (último dia): faltam 45 dia(s) (01/11/2026)
```

## 2. O fonte sai do PC com um comando — e só uma vez

`kansas/tools/bootstrap-app-to-cloud.ps1`. Não pede path, não pede senha, não
pede que você crie repositório nem cole secret:

```powershell
# ensaio — mostra tudo que faria, sem tocar em nada
pwsh -File kansas\tools\bootstrap-app-to-cloud.ps1 -DryRun

# de verdade
pwsh -File kansas\tools\bootstrap-app-to-cloud.ps1
```

O que ele faz, na ordem:

1. **acha o fonte sozinho** — varre `C:\Dev`, Downloads, Documents e o perfil
   procurando o `build.gradle` que contém `com.pulsefinanceiro.dreai`;
2. lê os fatos: `applicationId`, `targetSdk`, `versionCode`, `versionName`,
   config de assinatura;
3. **para na hora** se o `applicationId` não for o do app publicado — trocar
   isso faria a Play tratar como outro app;
4. monta uma **cópia limpa**: sem `node_modules`, `build`, `.gradle`, keystore,
   `.env`, `local.properties`, e **sem a história do git** (segredo que você
   commitou um dia não viaja junto);
5. **sanitiza o `gradle.properties`**: tira as linhas de senha, mantém o resto;
6. **varre a cópia atrás de segredo** (chave privada, senha em texto, chave de
   API, service account) e **aborta sem enviar nada** se achar;
7. instala o `gh` e o `git` via winget se faltarem;
8. cria o repositório **privado** `kansas-app` e sobe a cópia;
9. grava as secrets de assinatura com `gh secret set` — a keystore vira base64
   direto no stdin, **nunca** passa por arquivo no repo nem aparece em log;
10. instala os workflows de release e de vigia no repositório novo;
11. avisa no seu Telegram que terminou.

Tudo isso foi executado aqui em ensaio, no PowerShell 7.6.6, contra um projeto
React Native de teste. Os dois caminhos críticos foram provados:

| Teste | Resultado |
|---|---|
| descoberta automática, sem informar o caminho | achou o projeto pelo `applicationId` |
| senha no `gradle.properties` | removida da cópia (só `KEY_ALIAS` sobrou) |
| chave privada plantada na cópia | **abortou**, nada enviado, exit 1 |
| `node_modules`, `build`, `.env`, keystore | fora da cópia |

## 3. O que ainda não consigo fazer sozinho

| Item | Por quê |
|---|---|
| `gh auth login` na primeira vez | é um clique no navegador, uma vez; se você já usa `gh`, nem aparece |
| service account da Play | criada no Google Cloud + acesso concedido no Play Console; nenhuma API cria isso do zero |
| verificação de desenvolvedor (30/09) | status só existe na home do Play Console |

Tentei criar o repositório privado a partir daqui: a API do GitHub responde
**403 — "Resource not accessible by integration"**. Por isso a criação foi para
o script via `gh`, que usa a sua própria credencial e resolve repositório **e**
secrets no mesmo passo.
