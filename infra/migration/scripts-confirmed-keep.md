# Scripts confirmados pra migração — gate humano

approved-by: <pendente — usuário aprova no Telegram após F5>
approved-at: <pendente>

## Aprovados

| # | Nome | Path original (PC) | Decisão | Workflow correspondente |
|---|------|---------------------|---------|--------------------------|
|   |      |                     |         |                          |

(Preenchido pelo ChatGPT após resposta do usuário no Telegram.)

## Descartados

| # | Nome | Path original (PC) | Motivo |
|---|------|---------------------|--------|
|   |      |                     |        |

## Melhorias antes de migrar

| # | Nome | Path original (PC) | Diff necessário |
|---|------|---------------------|------------------|
|   |      |                     |                  |

---

## Regras

1. Claude NÃO executa migração de nenhum script sem este arquivo ter `approved-by` preenchido com nome real (não vazio, não placeholder).
2. Cada linha em "Aprovados" gera 3 arquivos no repo:
   - `infra/migration/scripts/<nome>/Dockerfile`
   - `infra/migration/scripts/<nome>/entrypoint.sh`
   - `workflows/30-<nome>.json`
3. ChatGPT faz upload pra `/opt/automacoes/<nome>/` no VPS via Hostinger MCP e importa workflow via n8nOps.
