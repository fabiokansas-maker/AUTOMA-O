# Policy — ChatGPT Command Bridge

A policy é decidida em duas dimensões:

- `action` (o que faz)
- `target_system` (onde)

A regra mais restritiva vence. Quando o action está em duas categorias
(ex: na lista de auto e na lista de bloqueio por contexto), bloqueia.

## auto — execução imediata, sem aprovação

| action               | observação                                  |
|----------------------|---------------------------------------------|
| healthcheck          | qualquer target                              |
| export_workflow      | n8n; só leitura                              |
| inspect_workflow     | n8n; só leitura                              |
| check_vps_disk       | vpsops; df -h, du em paths whitelisted       |
| generate_report      | drive; só escreve em pasta da bridge         |
| send_jarvis_status   | jarvis; canal interno                        |
| write_drive_report   | drive; só na folder da bridge                |

## approval — só roda depois de /bridge aprovar

| action                  | razão                                  |
|-------------------------|----------------------------------------|
| update_workflow         | muda produção                          |
| activate_workflow       | muda produção                          |
| restart_safe            | reinicia serviço                       |
| send_email              | comunicação externa                    |
| send_telegram_external  | comunicação externa                    |
| produce_ebook           | custo (LLM + render)                   |
| paid_api_call           | custo                                  |
| create_workflow         | muda produção                          |
| run_workflow            | só auto se o workflow estiver na allowlist `workflows_auto` |
| run_hotmart_worker      | toca dinheiro                          |
| send_jarvis_message     | mensagem externa do Jarvis             |

## blocked — n8n recusa direto, escreve em logs

- delete database
- delete docker volume
- expose secrets
- copy passwords
- use personal Instagram
- mass message
- spam
- `rm -rf` em qualquer payload
- `docker prune volumes`
- qualquer payload contendo strings: `/etc/shadow`, `id_rsa`, `.env`,
  `OPENAI_API_KEY`, `HOSTINGER_TOKEN`

## Como o n8n aplica

1. Lê linha de `commands` com status=new
2. Carrega `policy` (aba) na memória
3. Resolve action+target → veredito `auto | approval | blocked`
4. Faz match de blocked tokens no `payload_json` (regex case-insensitive)
5. Decide:
   - `auto`     → status=picked, executa, escreve result
   - `approval` → status=awaiting_approval, copia para pending_approval, ping Jarvis
   - `blocked`  → status=blocked, escreve log, ping Jarvis
