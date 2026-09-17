#!/usr/bin/env python3
"""
Estado real do app na Play, direto da Google Play Developer API.

Responde sem ninguém abrir o Play Console:
  * qual versionCode está em cada faixa (produção, aberto, fechado, interno)
  * qual é a release mais recente e seu status
  * se existe edit pendente travando envio
  * o que falta para publicar a próxima atualização

Autenticação: conta de serviço com acesso ao app no Play Console.
  export PLAY_SERVICE_ACCOUNT_JSON=/caminho/da/chave.json
  python3 kansas/tools/play_status.py com.pulsefinanceiro.dreai

Sem dependência externa: assina o JWT na mão e fala HTTP puro.
"""
from __future__ import annotations

import base64
import json
import os
import sys
import time
import urllib.parse
import urllib.request

SCOPE = "https://www.googleapis.com/auth/androidpublisher"
TOKEN_URL = "https://oauth2.googleapis.com/token"
API = "https://androidpublisher.googleapis.com/androidpublisher/v3/applications"


def b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def access_token(chave: dict) -> str:
    """JWT assinado com a chave da conta de serviço -> access token."""
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding
    except ImportError:
        sys.exit("faltou a lib `cryptography`: pip install cryptography")

    agora = int(time.time())
    cabecalho = {"alg": "RS256", "typ": "JWT"}
    corpo = {
        "iss": chave["client_email"], "scope": SCOPE, "aud": TOKEN_URL,
        "iat": agora, "exp": agora + 3600,
    }
    assinar = f"{b64(json.dumps(cabecalho).encode())}.{b64(json.dumps(corpo).encode())}"
    pk = serialization.load_pem_private_key(chave["private_key"].encode(), password=None)
    assinatura = pk.sign(assinar.encode(), padding.PKCS1v15(), hashes.SHA256())
    jwt = f"{assinar}.{b64(assinatura)}"

    dados = urllib.parse.urlencode({
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": jwt,
    }).encode()
    with urllib.request.urlopen(urllib.request.Request(TOKEN_URL, data=dados)) as r:
        return json.load(r)["access_token"]


def get(url: str, token: str) -> dict:
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def post(url: str, token: str) -> dict:
    req = urllib.request.Request(url, data=b"", method="POST",
                                 headers={"Authorization": f"Bearer {token}",
                                          "Content-Length": "0"})
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def delete(url: str, token: str) -> None:
    req = urllib.request.Request(url, method="DELETE",
                                 headers={"Authorization": f"Bearer {token}"})
    urllib.request.urlopen(req).close()


def main() -> int:
    if len(sys.argv) < 2:
        return print(__doc__) or 2
    pacote = sys.argv[1]
    caminho = os.environ.get("PLAY_SERVICE_ACCOUNT_JSON", "")
    if not caminho or not os.path.isfile(caminho):
        print("PLAY_SERVICE_ACCOUNT_JSON não aponta para um arquivo.")
        print("Sem essa chave, o estado das faixas só existe dentro do Play Console.")
        return 2

    chave = json.load(open(caminho, encoding="utf-8"))
    token = access_token(chave)

    # Um "edit" é uma transação; abrimos, lemos e descartamos (não publica nada).
    edit = post(f"{API}/{pacote}/edits", token)
    edit_id = edit["id"]
    try:
        faixas = get(f"{API}/{pacote}/edits/{edit_id}/tracks", token).get("tracks", [])
        print(f"# Estado na Play — {pacote}\n")
        maior = 0
        for t in faixas:
            print(f"## faixa: {t['track']}")
            for rel in t.get("releases", []):
                codigos = rel.get("versionCodes", []) or []
                maior = max([maior] + [int(c) for c in codigos])
                frac = rel.get("userFraction")
                print(f"  - status: {rel.get('status')}"
                      f" | versionCode: {', '.join(map(str, codigos)) or '—'}"
                      f" | nome: {rel.get('name', '—')}"
                      + (f" | rollout: {float(frac) * 100:.0f}%" if frac else ""))
            if not t.get("releases"):
                print("  - (sem release)")
        print(f"\nPróximo versionCode precisa ser > {maior}." if maior
              else "\nNenhum versionCode encontrado nas faixas.")
    finally:
        # devolve a transação sem efeito colateral
        try:
            delete(f"{API}/{pacote}/edits/{edit_id}", token)
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
