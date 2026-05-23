# Política de backup AUTOMA-O

## Escopo

| Item | Frequência | Retenção local | Retenção Drive |
|------|-----------|----------------|----------------|
| Postgres n8n (pg_dump) | diário 03h00 BRT | 7 dias | 30 dias |
| Volume `n8n-mryj_n8n_data` (tar.gz) | diário 03h00 BRT | 7 dias | 30 dias |
| `/opt/automacoes/` (tar.gz) | diário 03h00 BRT | 7 dias | 30 dias |
| Postgres `automao` (vagas + matches) | diário 03h00 BRT | 7 dias | 30 dias |

## Orquestrador

`workflows/09-backup-daily.json` no n8n-mryj. Cron `0 3 * * *` TZ America/Sao_Paulo.

## Destinos

- **Local:** `/opt/backups/`. Permissão 0700, dono root.
- **Drive:** pasta `AUTOMA-O/Backups/<YYYY-MM>/` via credential `google-drive-fabio` (OAuth criptografado no n8n).

## RTO esperado

- Restauração Postgres do n8n: ≤15min (pg_restore + n8n restart).
- Restauração workflow específico: ≤2min (n8n import:workflow).
- Restauração `/opt/automacoes`: ≤5min (tar + docker compose up).

## Garantias

- On-error branch do workflow → Telegram "BACKUP FALHOU" com stack.
- Healthcheck (workflow 10) testa Drive credential via getMe equivalente do bot.
- Tamanho dos 3 arquivos reportado no Telegram a cada sucesso.

## Limitações conhecidas

- Backup Postgres do n8n é dump lógico (não físico). Para uma restauração ponto-a-ponto seria preciso WAL archiving — não está habilitado.
- Volume `n8n_data` é taradoneado AO VIVO (sem `docker stop`). Risco residual de corrupção de SQLite se ainda for SQLite. Após padronização (Postgres), o volume contém apenas binários/encryption-key — risco ≈ zero.

## Senha de criptografia (n8n)

`N8N_ENCRYPTION_KEY` no env do container. Sem ela, credentials no Postgres do n8n são ilegíveis após restore. **Cópia segura desta key fora do VPS é responsabilidade do usuário** (e.g., gerenciador de senhas). Não vai pro repo.
