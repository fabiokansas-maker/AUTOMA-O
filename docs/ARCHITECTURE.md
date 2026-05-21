# Arquitetura — ChatGPT Command Bridge

## Camadas

| camada            | papel                                                         |
|-------------------|---------------------------------------------------------------|
| ChatGPT           | produtor de comandos, leitor de resultados                    |
| Google Sheet      | fila + memória compartilhada (commands, results, logs, etc.)  |
| Google Drive      | anexos pesados: relatórios, exports, screenshots              |
| n8n               | executor: lê Sheet, aplica policy, chama backends             |
| vpsOps / API Ops  | backend de execução real na VPS                                |
| Jarvis            | canal humano (aprovação manual via /bridge)                   |

## Contrato de comando (Sheets!commands)

| coluna             | tipo     | obrigatório | descrição                                          |
|--------------------|----------|-------------|----------------------------------------------------|
| command_id         | uuid     | sim         | gerado pelo produtor                                |
| created_at         | iso8601  | sim         | UTC                                                 |
| source             | enum     | sim         | chatgpt, jarvis, manual                             |
| target_system      | enum     | sim         | vpsops, n8n, jarvis, hotmart, freela, vendas,       |
|                    |          |             | telegram, claude_design, drive, gmail               |
| action             | enum     | sim         | ver lista em POLICY.md                              |
| payload_json       | json     | sim         | parâmetros do action                                |
| priority           | int      | não         | 1 (alto) a 5 (baixo). default 3                     |
| status             | enum     | sim         | new, picked, running, done, error, awaiting_approval, blocked |
| requires_approval  | bool     | -           | preenchido pelo n8n após aplicar policy             |
| approved           | bool     | -           | preenchido por /bridge aprovar                      |
| result_id          | uuid     | -           | aponta para linha em results                        |
| notes              | string   | -           | livre                                                |

## Transições de status

```
new ──► picked ──► running ──► done
                           └──► error
new ──► awaiting_approval ──► (aprovado)  ──► picked
                          └─► (recusado)  ──► blocked
new ──► blocked   (policy bloqueou direto)
```

## Contrato de resultado (Sheets!results)

| coluna        | descrição                                            |
|---------------|------------------------------------------------------|
| result_id     | uuid                                                  |
| command_id    | FK para commands                                      |
| started_at    | iso8601                                               |
| finished_at   | iso8601                                               |
| exit_code     | 0 ok, !=0 erro                                        |
| summary       | até 500 chars                                         |
| drive_link    | link público do relatório completo (se houver)        |
| payload_out   | json com dados estruturados                           |

## Logs (Sheets!logs)

Append-only. Cada evento relevante (policy decision, retry, erro) vira
uma linha. Serve para auditoria e debug.

## Pending approval (Sheets!pending_approval)

Cópia mínima de commands com `requires_approval=true & approved=null`.
É o que `/bridge pendentes` lê.

## Policy (Sheets!policy)

Versão de runtime do `docs/POLICY.md`. Mudou? Atualiza a aba — o n8n
relê a cada execução.

## Provisionamento manual (one-time)

1. Criar Sheet **ChatGPT Command Bridge** no Drive do Fabio
2. Criar abas conforme `sheets/schema.json`
3. Importar `sheets/seed.csv` em cada aba para popular headers + policy
4. Criar pasta Drive **chatgpt-bridge-reports** — pegar `folder_id`
5. Compartilhar Sheet e folder com a Service Account do n8n (editor)
6. Importar `n8n/chatgpt-command-bridge-monitor-v1.json` no n8n
7. Substituir os placeholders no workflow:
   - `__SHEET_ID__`
   - `__DRIVE_FOLDER_ID__`
   - `__VPSOPS_BASE_URL__`
   - `__JARVIS_WEBHOOK__`
8. Ativar o workflow
9. Rodar `scripts/test_healthcheck.sh` para o smoke test ponta-a-ponta
