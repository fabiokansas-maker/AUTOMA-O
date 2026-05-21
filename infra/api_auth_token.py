#!/usr/bin/env python3
"""Gera API_AUTH_TOKEN forte para o ops_api_gateway.py do ChatGPT.

Uso:
    python3 infra/api_auth_token.py

Imprime UM token de 32 bytes (64 chars hex) no stdout. Não persiste em arquivo.
Você (ou o ChatGPT via Hostinger MCP) deve copiar e armazenar como variável de
ambiente no host de produção:

    1. No serviço systemd que roda o gateway:
       sudo systemctl edit ops-api-gateway.service
       [Service]
       Environment="API_AUTH_TOKEN=<cole aqui>"
       sudo systemctl daemon-reload
       sudo systemctl restart ops-api-gateway.service

    2. Para clientes consumindo /api/ops/*:
       export API_AUTH_TOKEN=<cole aqui>
       curl -H "Authorization: Bearer $API_AUTH_TOKEN" \
            https://<host>/api/ops/health

O token NÃO entra em git, Markdown, chat, README, .env commitado.
"""

from __future__ import annotations

import secrets
import sys


def main() -> int:
    # 32 bytes = 256 bits de entropia = inquebrável por brute force em prazo prático.
    token = secrets.token_hex(32)
    print(token)
    print(
        "\n# Token gerado. NÃO commite. Armazene em env seguro do host de produção.",
        file=sys.stderr,
    )
    print(
        f"# Tamanho: {len(token)} chars hex ({len(token)*4} bits de entropia)",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
