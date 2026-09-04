---
session: b9a215c3-2fe4-5a92-bf2a-b20226cb7440
agent: claude
ts: 2026-09-04T10:00:00Z
status: completed
tags: [dinheiro-em-dia, google-play, android-developer-verification, chave-assinatura]
---

# E-mail da chave (04/09/2026) — Android Developer Verification, NÃO é problema no app

## O e-mail

- Remetente: `googleplay-noreply@google.com`
- Data: **2026-09-04 02:45 UTC**, thread `1a06a4e38073cc86`, ainda na INBOX
- Assunto: "FABIOKANSAS: [Último lembrete] Registre seus apps e chaves de assinatura
  para atender aos requisitos da verificação de desenvolvedor Android até
  **30 de setembro de 2026**"
- Já tinha vindo um "[Lembrete]" igual em **2026-08-07** (thread `19fdd34bd4facb23`)

## O que ele diz de fato

Regra nova do Play: todo app precisa estar **registrado** (par nome-do-pacote +
chave de assinatura) até **30/09/2026**, senão é removido da plataforma no mundo
todo. A partir dessa data, apps distribuídos fora do Play em regiões selecionadas
também só instalam em Android certificado se o dev for verificado.

**Ponto central: é e-mail de conta inteira (FABIOKANSAS), não é alerta de app.**
Não cita `Dinheiro em Dia` em lugar nenhum. Google diz que **auto-registrou +99%**
dos apps — todos os que usam **Play App Signing** (chave de assinatura gerenciada
pelo Google).

Ação só é necessária para:
1. apps do Play que NÃO foram auto-registrados
2. apps distribuídos fora do Play (sideload / lojas alternativas)
3. chaves extras usadas para assinar fora do Play

## Por que o Dinheiro em Dia está coberto (evidência, não chute)

O e-mail de **2026-05-06** (`noreply-play-console@google.com`, thread
`19dfdfdecfcd3769`) confirma reset de **chave de upload** do
`com.pulsefinanceiro.dreai`, com link direto para
`.../app/4972607150651484511/keymanagement?tab=appSigning`.

**Chave de upload só existe quando Play App Signing está ligado.** Logo o app está
no bucket auto-registrado dos +99%. Nada a fazer para ele nesse prazo de 30/09.

IDs úteis extraídos daí:
- developer account id: `5121667904184895227`
- app id (Dinheiro em Dia): `4972607150651484511`
- fingerprints da chave de UPLOAD (não é a de assinatura):
  - SHA1 `DA:F2:3B:DF:03:04:B2:BD:AD:12:54:51:9F:18:23:5D:65:00:A5:D4`
  - MD5 `25:12:EB:C8:27:C6:52:6F:65:F9:73:2C:AA:87:7F:CF`

## Limitação real de automação (registrar aqui pra ninguém perder tempo)

A página `play.google.com/console/android-developer-verification` é **web-only**.
A Google Play Developer API (`androidpublisher v3`) **não expõe** status de
registro/verificação — nem endpoint de listar apps da conta. Então nenhum agente
consegue confirmar o status por API. As únicas fontes possíveis são:
- a home do Play Console (filtro "não registrados"), ou
- e-mail de escalonamento do Google, se vier.

## O que realmente corre risco nessa conta (e não é esse e-mail)

| App | Pendência | Prazo |
|---|---|---|
| **Atende Certo** | target API level antigo | 31/08/2026 — **VENCIDO** |
| **Aura do Clima** | target API level + Play Billing Library descontinuada | 31/08/2026 — **VENCIDO** |
| **Dinheiro em Dia** | rejeição de 01/07 por falta de conta demo (Sign in details) | sem prazo, mas bloqueia updates |

O aviso de target API level (21/07, thread `19f86c6710b56e12`) cita **só** Atende
Certo e Aura do Clima. Dinheiro em Dia não está nele.
