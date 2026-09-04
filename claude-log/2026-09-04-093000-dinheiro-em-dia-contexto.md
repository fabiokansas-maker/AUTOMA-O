---
session: b9a215c3-2fe4-5a92-bf2a-b20226cb7440
agent: claude
ts: 2026-09-04T09:30:00Z
status: in_progress
tags: [dinheiro-em-dia, app, google-play, firebase]
---

# Dinheiro em Dia — contexto reconstruído (fonte: Gmail + Drive + Play Console)

Contexto levantado porque **não existe nenhum código do app neste repo**. O repo
AUTOMA-O na branch ativa não tem uma linha do Dinheiro em Dia. Tudo abaixo veio de
e-mail (Gmail MCP) e Drive — registrando aqui pra outros agentes não precisarem
redescobrir.

## Identidade do app

| Campo | Valor |
|---|---|
| Nome na loja | **Dinheiro em Dia** |
| Package | `com.pulsefinanceiro.dreai` |
| Conta dev Play | FABIOKANSAS |
| Projeto Firebase / GCP | `dinheiro-em-dia-1` |
| Login | Sign in with Google (Google Identity) — confirmado por e-mail de consentimento OAuth em 2026-07-26 |
| Classificação IARC | ID `a2fd8172-9a9b-8707-8830-3f5d95e900ad` (rating emitido 2026-07-09) |
| Provável fonte-fonte | `APP FINANCEIRO.zip` no Drive raiz (id `1mLEamZGHo1WlWtfYM-cU4sTlfxrnI0O3`, 4,05 GB, mod. 2026-04-24) |

## Linha do tempo real

| Data | Evento |
|---|---|
| 2026-04-05 | Recrutamento de testadores (Reddit r/TestersCommunity, grupos de teste cruzado) |
| 2026-04-11 | GCP `dinheiro-em-dia-1` **suspenso** por violação de ToS → **reinstaurado** no mesmo dia; Firebase upgrade de plano (billing account nova) |
| 2026-04-17/19 | Teste cruzado com outros devs (Water Tank Level, Calculadora de Fracciones) |
| 2026-05-06 | Solicitação de **reset da upload key** do Play |
| 2026-05-21 | Play: "More testing required to access production" |
| 2026-06-05 | Play: "More testing required" de novo |
| 2026-06-21 | **Acesso à produção concedido** |
| 2026-07-01 | **App REJEITADO** — Violation of Play Console Requirements |
| 2026-07-09 | IARC live rating emitido |
| 2026-07-26 | Login com Google usado no app (app funcionando) |

## Bloqueio ATUAL (não resolvido até 2026-09-04)

**App Status: Rejected** (e-mail 2026-07-01, ainda UNREAD na inbox).

Motivo: **"Missing demo or guest account details"** — o revisor do Google não
conseguiu entrar no app porque o app exige login (Sign in with Google) e não foi
declarada conta de demonstração.

Não é bug de código. Não é política de conteúdo financeiro. É preenchimento de
formulário no Play Console:

1. Play Console → App content → **Sign in details** (Detalhes de login)
2. Declarar usuário + senha de uma conta demo que já tenha dados semeados
3. Se alguma função for restrita, escrever instruções de acesso
4. Publishing overview → **Send changes for review**

Anexo do e-mail: `IN_APP_EXPERIENCE-5362.png` (thread `19f1e16e3f9131e5`).

Atenção: como o login é Google Sign-In, uma conta demo com e-mail/senha pode não
funcionar direto no fluxo OAuth. Os dois caminhos que costumam destravar isso:
- adicionar um **botão "Entrar como convidado" / modo demo** no app (backdoor de
  review com credencial fixa), ou
- criar uma conta Google de teste dedicada e passar as credenciais nos Sign in
  details, o que exige desativar 2FA nessa conta.

## Outros apps na mesma conta dev (não confundir)

- **Atende Certo** — precisa subir target API level até 31/08/2026 (prazo já vencido)
- **Aura do Clima** — target API level + Biblioteca Play Faturamento descontinuada
- (app de nível de caixa d'água usado só em teste cruzado)

O aviso de target API level de 2026-07-21 **não** atinge o Dinheiro em Dia.

## Onde o código NÃO está

- ❌ repo `fabiokansas-maker/AUTOMA-O` (nenhuma das 3 branches tem código do app)
- ❌ Supabase (`cockpit-fabio` e o projeto inativo não têm nada do app)
- ✅ candidato único: `APP FINANCEIRO.zip` no Drive (4 GB — provável projeto
  Flutter/RN com build artifacts junto)

## Próximo passo sugerido

Nada aqui exige clique do usuário exceto o preenchimento dos Sign in details no
Play Console (não há API pública do Play Console para esse campo). O que dá pra
automatizar do lado do agente: baixar o `APP FINANCEIRO.zip`, achar o fluxo de
auth e implementar o modo convidado/demo, que remove a dependência de conta demo
e resolve a rejeição de forma permanente.
