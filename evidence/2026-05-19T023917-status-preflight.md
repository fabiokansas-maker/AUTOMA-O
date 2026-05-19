# Preflight — 2026-05-19T023917-status
ts: 2026-05-19T02:39:29Z
action: status

❌ Secrets faltando:
- HOSTINGER_SSH_HOST
- HOSTINGER_SSH_USER
- HOSTINGER_SSH_KEY ou HOSTINGER_SSH_PASSWORD

## Para cadastrar
GitHub → fabiokansas-maker/AUTOMA-O → Settings → Secrets and variables → Actions → New repository secret

Cole os valores:
- HOSTINGER_SSH_HOST = 187.124.132.108
- HOSTINGER_SSH_USER = root
- HOSTINGER_SSH_PORT = 22
- HOSTINGER_SSH_PASSWORD = <senha root da VPS>
OU
- HOSTINGER_SSH_KEY = <chave privada SSH OpenSSH PEM>
