import hmac
import os
import threading

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from waitress import serve

import memoria
import tempo
from cerebro import criar_conversa, responder

load_dotenv()

SENHA = os.getenv("EVY_SENHA", "")
PASTA_WEB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")

app = Flask(__name__, static_folder=None)
trava = threading.Lock()
conversa = criar_conversa()


def autorizado():
    enviada = request.headers.get("X-Evy-Senha", "")
    return bool(SENHA) and hmac.compare_digest(enviada.encode(), SENHA.encode())


@app.get("/")
def pagina():
    return send_from_directory(PASTA_WEB, "index.html")


@app.get("/web/<path:arquivo>")
def arquivos(arquivo):
    return send_from_directory(PASTA_WEB, arquivo)


@app.get("/manifest.webmanifest")
def manifesto():
    return send_from_directory(
        PASTA_WEB, "manifest.json", mimetype="application/manifest+json"
    )


@app.get("/sw.js")
def service_worker():
    resposta = send_from_directory(PASTA_WEB, "sw.js", mimetype="text/javascript")
    resposta.headers["Cache-Control"] = "no-cache"
    return resposta


@app.get("/api/historico")
def historico():
    if not autorizado():
        return jsonify(erro="Senha incorreta."), 401
    with trava:
        mensagens = [
            {"papel": m["papel"], "texto": tempo.remover_contexto(m["texto"])}
            for m in memoria.carregar_historico()
        ]
        return jsonify(mensagens=mensagens)


@app.post("/api/mensagem")
def mensagem():
    if not autorizado():
        return jsonify(erro="Senha incorreta."), 401
    dados = request.get_json(silent=True) or {}
    texto = str(dados.get("mensagem", "")).strip()
    if not texto:
        return jsonify(erro="Mensagem vazia."), 400
    with trava:
        try:
            resposta = responder(conversa, texto)
        except Exception as erro:
            return jsonify(erro=str(erro)), 500
    return jsonify(resposta=resposta or "(sem resposta)")


if __name__ == "__main__":
    if not SENHA:
        raise SystemExit("Defina EVY_SENHA no arquivo .env antes de iniciar.")
    print("Evy no ar, na porta 5000 (somente local).")
    serve(app, host="127.0.0.1", port=5000)
