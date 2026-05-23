# Inventário PC do usuário — &lt;YYYY-MM-DD&gt;

ChatGPT preenche via acesso filesystem do PC (`C:\Users\fabio\`). Claude analisa depois.

## Pastas-candidatas

Mapear cada uma com árvore depth 2, tamanho, mtime, deps, credenciais hardcoded, trigger atual, output.

| Pasta | Tamanho | Última mod | Linguagem dominante | Trigger atual | Output |
|-------|---------|-----------|---------------------|---------------|--------|
| `C:\Users\fabio\automacoes\` | | | | | |
| `C:\Users\fabio\Downloads\access-registry-vpsops\` | | | | | |
| `C:\Users\fabio\FreelaOps\` | | | | | |
| `C:\Users\fabio\OpenClaw\` | | | | | |
| `C:\Users\fabio\JarvisHotmart\` | | | | | |
| `C:\Users\fabio\` (outras pastas relevantes) | | | | | |

## Por pasta — detalhamento

### `<pasta>`

**Árvore (depth 2):**
```
<saída de `tree /F /A` ou `ls -la`>
```

**Deps:**
- `requirements.txt`: …
- `package.json`: …
- Outros (Dockerfile, pyproject.toml, etc): …

**Credenciais hardcoded (grep `API_KEY|PASSWORD|TOKEN|SECRET` ignore-case):**
```
<saída — REDIGIR valores reais; relatar apenas linha + chave>
```

**Trigger atual:**
- [ ] Cron Windows (Task Scheduler) — task name: `…`
- [ ] Clique manual (.bat / .ps1 / atalho)
- [ ] Webhook
- [ ] Outro: `…`

**Output (onde a saída vai):**
- [ ] Google Drive (folder: `…`)
- [ ] Google Sheet (id: `…`)
- [ ] Telegram (chat: `…`)
- [ ] Email
- [ ] Stdout/arquivo local em `…`

**Faz dinheiro? (decisão do usuário no Telegram depois)**
- [ ] Sim (mantém / migra)
- [ ] Não (descarta)
- [ ] Talvez (Claude propõe melhoria)

**Observações:**
…

## Resumo

- Total de scripts encontrados: 
- Total identificados como "gera dinheiro": 
- Total propostos para descarte: 
- Total propostos para melhoria antes de migrar: 

## Próximo passo

Claude lê este arquivo e preenche `infra/migration/migration-decision-matrix.md`.
