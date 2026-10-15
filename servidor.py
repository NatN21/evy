import os
import threading
import time

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from waitress import serve

import dispositivos
import lembretes
import memoria
import push
import tempo
from cerebro import criar_conversa, responder

load_dotenv()

PASTA_WEB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")

app = Flask(__name__, static_folder=None)
trava = threading.Lock()


COOKIE = "evy_dispositivo"


def autorizado():
    return dispositivos.verificar(request.cookies.get(COOKIE))


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
        return jsonify(erro="Não autorizado."), 401
    with trava:
        mensagens = [
            {"papel": m["papel"], "texto": tempo.remover_contexto(m["texto"])}
            for m in memoria.carregar_historico()
        ]
    return jsonify(mensagens=mensagens)


@app.post("/api/mensagem")
def mensagem():
    if not autorizado():
        return jsonify(erro="Não autorizado."), 401
    dados = request.get_json(silent=True) or {}
    texto = str(dados.get("mensagem", "")).strip()
    if not texto:
        return jsonify(erro="Mensagem vazia."), 400
    with trava:
        try:
            resposta = responder(criar_conversa(), texto)
        except Exception:
            return (
                jsonify(erro="Não consegui responder agora. Tente novamente mais tarde."),
                500,
            )
    return jsonify(resposta=resposta or "(sem resposta)")


@app.get("/api/memoria")
def ver_memoria():
    if not autorizado():
        return jsonify(erro="Não autorizado."), 401
    with trava:
        fatos = memoria.carregar_fatos()
    return jsonify(fatos=fatos)


@app.post("/api/memoria/apagar")
def apagar_memoria():
    if not autorizado():
        return jsonify(erro="Não autorizado."), 401
    dados = request.get_json(silent=True) or {}
    fato = str(dados.get("fato", ""))
    with trava:
        apagado = memoria.apagar_fato_por_texto(fato)
    if not apagado:
        return jsonify(erro="Essa lembrança não foi encontrada."), 404
    return jsonify(ok=True)


@app.get("/api/lembretes")
def ver_lembretes():
    if not autorizado():
        return jsonify(erro="Não autorizado."), 401
    with trava:
        itens = lembretes.para_painel()
    return jsonify(lembretes=itens)


@app.post("/api/lembretes/apagar")
def apagar_lembrete():
    if not autorizado():
        return jsonify(erro="Não autorizado."), 401
    dados = request.get_json(silent=True) or {}
    id_lembrete = str(dados.get("id", ""))
    with trava:
        apagado = lembretes.apagar(id_lembrete)
    if not apagado:
        return jsonify(erro="Esse lembrete não foi encontrado."), 404
    return jsonify(ok=True)

@app.get("/parear")
def pagina_parear():
    return send_from_directory(PASTA_WEB, "parear.html")


@app.post("/api/parear")
def parear_dispositivo():
    dados = request.get_json(silent=True) or {}
    nome = str(dados.get("nome", "")).strip()[:40] or "Aparelho"
    try:
        token = dispositivos.parear(str(dados.get("codigo", "")), nome)
    except dispositivos.Bloqueado:
        return jsonify(erro="Muitas tentativas. Aguarde alguns minutos."), 429
    if not token:
        return jsonify(erro="Código inválido ou expirado."), 401
    resposta = jsonify(ok=True)
    resposta.set_cookie(
        COOKIE,
        token,
        max_age=60 * 60 * 24 * 365,
        httponly=True,
        secure=True,
        samesite="Strict",
    )
    return resposta


@app.get("/api/eu")
def eu():
    return jsonify(autorizado=autorizado())


@app.get("/api/dispositivos")
def ver_dispositivos():
    if not autorizado():
        return jsonify(erro="Não autorizado."), 401
    return jsonify(dispositivos=dispositivos.listar())


@app.post("/api/dispositivos/revogar")
def revogar_dispositivo():
    if not autorizado():
        return jsonify(erro="Não autorizado."), 401
    dados = request.get_json(silent=True) or {}
    if not dispositivos.revogar(str(dados.get("id", ""))):
        return jsonify(erro="Dispositivo não encontrado."), 404
    return jsonify(ok=True)

VAPID_PUBLICA = os.getenv("VAPID_PUBLICA", "")


@app.get("/api/push/chave")
def chave_push():
    if not autorizado():
        return jsonify(erro="Não autorizado."), 401
    return jsonify(chave=VAPID_PUBLICA)


@app.post("/api/push/inscrever")
def inscrever_push():
    if not autorizado():
        return jsonify(erro="Não autorizado."), 401
    inscricao = request.get_json(silent=True) or {}
    if not inscricao.get("endpoint"):
        return jsonify(erro="Inscrição inválida."), 400
    push.inscrever(inscricao)
    return jsonify(ok=True)


@app.post("/api/push/testar")
def testar_push():
    if not autorizado():
        return jsonify(erro="Não autorizado."), 401
    enviados = push.enviar("Evy", "Aviso de teste: está tudo funcionando.")
    if enviados == 0:
        return jsonify(erro="Nenhum aparelho recebeu. Ative os avisos primeiro."), 400
    return jsonify(ok=True, enviados=enviados)


def verificar_lembretes():
    while True:
        try:
            with trava:
                vencidos = lembretes.pendentes_para_avisar()
            for lembrete in vencidos:
                atrasado = lembretes.atraso_em_minutos(lembrete) > 10
                titulo = "Lembrete atrasado" if atrasado else "Lembrete"
                if push.enviar(titulo, lembrete["texto"]) > 0:
                    with trava:
                        lembretes.marcar_avisado(lembrete["id"])
            with trava:
                lembretes.limpar_antigos()
        except Exception as erro:
            print("Erro no verificador de lembretes:", erro)
        time.sleep(20)


def iniciar_avisos():
    threading.Thread(target=verificar_lembretes, daemon=True).start()


if __name__ == "__main__":
    iniciar_avisos()
    print("Evy no ar, na porta 5000 (somente local).")
    serve(app, host="127.0.0.1", port=5000)
