# scripts/

## install-pc-sync (rode no seu PC, uma vez)

Configura sync automático deste repo → pasta `Claude/` do seu vault Obsidian
(a cada 5 min). NÃO depende de n8n nem Google Drive — usa só `git pull` agendado.

### Linux / macOS

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/fabiokansas-maker/automa-o/claude/download-local-files-5hfmT/scripts/install-pc-sync.sh)
```

### Windows (PowerShell)

```powershell
irm https://raw.githubusercontent.com/fabiokansas-maker/automa-o/claude/download-local-files-5hfmT/scripts/install-pc-sync.ps1 | iex
```

O script pergunta onde está seu vault e cria `<vault>/Claude/automa-o`. Cron/launchd/Task Scheduler
faz `git pull` a cada 5 min — quando o PC tá online, ele atualiza; quando tá off, retoma quando ligar.

## claude-log.sh

Helper que EU (Claude) uso pra commitar updates de progresso em `claude-log/`.
Não precisa rodar isso — é chamado automaticamente durante sessões.

## _pull-loop.{sh,ps1}

Criados pelo `install-pc-sync` dentro do clone local. Não use direto.
