import json
import os
import threading
from pathlib import Path

from pywebpush import WebPushException, webpush

PASTA_DADOS = Path(__file__).parent / "dados"
ARQUIVO = PASTA_DADOS / "inscricoes.json"
CHAVE_PRIVADA = PASTA_DADOS / "vapid" / "private_key.pem"

trava_push = threading.Lock()


def _carregar():
    if not ARQUIVO.exists():
        return []
    try:
        return json.loads(ARQUIVO.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def _salvar(lista):
    PASTA_DADOS.mkdir(exist_ok=True)
    ARQUIVO.write_text(json.dumps(lista, indent=2), encoding="utf-8")


def inscrever(inscricao):
    with trava_push:
        lista = [
            i for i in _carregar() if i.get("endpoint") != inscricao.get("endpoint")
        ]
        lista.append(inscricao)
        _salvar(lista)


def enviar(titulo, corpo):
    contato = os.getenv("VAPID_CONTATO", "")
    enviados = 0
    with trava_push:
        validas = []
        for inscricao in _carregar():
            try:
                webpush(
                    subscription_info=inscricao,
                    data=json.dumps({"titulo": titulo, "corpo": corpo}),
                    vapid_private_key=str(CHAVE_PRIVADA),
                    vapid_claims={"sub": contato},
                    ttl=86400,
                    headers={"Urgency": "high"},
                )
                validas.append(inscricao)
                enviados += 1
            except WebPushException as erro:
                resposta = erro.response
                status = resposta.status_code if resposta is not None else None
                if status in (404, 410):
                    continue
                validas.append(inscricao)
                print("Falha ao enviar aviso:", erro)
            except Exception as erro:
                validas.append(inscricao)
                print("Falha ao enviar aviso:", erro)
        _salvar(validas)
    return enviados
