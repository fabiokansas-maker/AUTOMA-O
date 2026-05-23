# Matriz de decisão — migração scripts PC → VPS

Preenchido por Claude após ChatGPT entregar `evidence/<data>-pc-inventory.md`. Usuário aprova no Telegram. Apenas scripts com `approved=true` em `scripts-confirmed-keep.md` são migrados.

| # | Script (path PC) | Decisão | Justificativa | Workflow n8n | Imagem Docker | Cron |
|---|------------------|---------|---------------|--------------|---------------|------|
| 1 | `…` | MIGRAR-CONTAINER | gera receita recorrente | `workflows/30-<nome>.json` | `python:3.12-slim` | diário 09h |
| 2 | `…` | DESCARTAR | duplica funcionalidade do registry | — | — | — |
| 3 | `…` | MELHORAR-ANTES | depende de UI do Windows; refatorar pra headless antes de migrar | TODO | TODO | TODO |
| 4 | `…` | MIGRAR-SYSTEMD | daemon long-running, não cron | — | — | n/a |
| 5 | `…` | MIGRAR-CRON | rodar 1×/semana, simples demais para workflow | — | — | `0 8 * * 1` |

## Opções de decisão

- **MIGRAR-CONTAINER** (default): script vira container, invocado por workflow n8n via Execute Command.
- **MIGRAR-SYSTEMD**: apenas se for daemon contínuo, raro.
- **MIGRAR-CRON**: apenas para frequência baixa (<1×/semana) e lógica trivial.
- **DESCARTAR**: motivar (obsoleto, duplica algo do registry, depende de software Windows GUI).
- **MELHORAR-ANTES**: Claude propõe diff específico antes de migrar.

## Workflow de aprovação

1. Claude commita esta matriz preenchida.
2. ChatGPT envia resumo no Telegram: "Confirmando: manter [N scripts], descartar [M], melhorar [K]. Responder OK/NOK/edits."
3. Usuário responde no Telegram.
4. ChatGPT atualiza `scripts-confirmed-keep.md` com `approved-by: fabio` no header.
5. Para cada aprovado: Claude commita o template preenchido em `infra/migration/scripts/<nome>/`.
6. ChatGPT faz upload pro VPS via Hostinger MCP em `/opt/automacoes/<nome>/`.
7. ChatGPT importa o workflow n8n correspondente via n8nOps.

## Critério de "gera dinheiro"

Direto:
- Vende serviço pra cliente externo (FreelaOps, OpenClaw API, JarvisHotmart).
- Aumenta candidaturas a vagas remuneradas (AUTOMA-O core).

Indireto (caso a caso):
- Ferramenta interna que reduz tempo manual recorrente (>2h/semana).

Não-dinheiro (descarte automático):
- POC abandonada > 3 meses sem commit.
- Wrapper trivial de algo já no registry.
- Dependente de UI Windows não-portável.
