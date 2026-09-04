---
session: b9a215c3-2fe4-5a92-bf2a-b20226cb7440
agent: claude
ts: 2026-09-04T11:00:00Z
status: completed
tags: [dinheiro-em-dia, google-play, decisao, nao-mexer]
---

# DECISÃO: o e-mail da chave não exige NENHUMA mudança de código

## Contexto

O usuário tem OUTRA atividade/sessão em andamento melhorando o app Dinheiro em Dia
e pediu explicitamente para não perder nada. Perguntou se dava pra "resolver isso
sem fazer merda".

## Resposta técnica

**Resolver = não fazer nada.** O e-mail de 04/09 (Android Developer Verification,
prazo 30/09/2026) é disparo de conta inteira e o app já está auto-registrado
porque usa Play App Signing (prova: reset de chave de UPLOAD em 06/05 apontando
para `keymanagement?tab=appSigning`). Não existe commit, build, upload de AAB nem
alteração de keystore que esse e-mail exija.

## Regra para qualquer agente que pegar esse contexto depois

**NÃO TOCAR** em código, keystore, `build.gradle`, `versionCode`, assinatura ou
qualquer artefato do Dinheiro em Dia por causa desse e-mail. Qualquer alteração
aqui é risco puro de conflito com o trabalho paralelo do usuário, sem nenhum
ganho. Se outro agente propuser "regenerar keystore" ou "resubir AAB" por causa
desse aviso, está errado — regenerar keystore com Play App Signing ligado é
justamente o caminho de quebrar a publicação.

## O que foi feito no lugar (risco zero)

Criada rotina agendada diária (12h BRT) que:
- lê só o Gmail atrás de e-mails novos do Play Console (2 dias)
- filtra ruído de assinatura pessoal (Tinder / Google One / Anthropic)
- avisa no Telegram `@Vagadeeemprego_bot` (chat 5772934753) SÓ se aparecer algo
  novo e acionável sobre registro, verificação, suspensão, remoção ou chave
- em silêncio se não houver nada
- proibida de tocar em código

Cobre o prazo de 30/09/2026 sem o usuário precisar abrir inbox nem Play Console.

## Pendências que continuam abertas (essas SIM exigem código, mas não agora)

| App | Pendência | Situação |
|---|---|---|
| Atende Certo | target API level | vencido 31/08 — bloqueia updates |
| Aura do Clima | target API level + Play Billing Library | vencido 31/08 — bloqueia updates |
| Dinheiro em Dia | rejeição 01/07 por falta de conta demo | pendente; melhor solução é modo convidado |

Só mexer nisso quando o usuário confirmar que a atividade paralela dele terminou
e disser onde está o código.
