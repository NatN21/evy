import time
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

import memoria
import tempo

load_dotenv()

MODELO = "gemini-3.5-flash-lite"
PASTA = Path(__file__).parent
PERSONALIDADE = (PASTA / "personalidade.txt").read_text(encoding="utf-8")

REGRAS_DE_TEMPO = (
    "Cada mensagem do Natan começa com uma linha [Contexto: ...] que informa a data, "
    "o dia da semana, a hora e há quanto tempo foi a última mensagem dele. "
    "Use isso para se situar no tempo: saiba que dia e hora são agora, perceba o que "
    "está próximo ou distante e quanto tempo passou. "
    "Quando passar bastante tempo (horas ou dias) e ele apenas cumprimentar, retome com "
    "naturalidade o que ele tinha mencionado antes, como eventos que já aconteceram, "
    "oportunidades ou preocupações, perguntando como foi, sem soar mecânica e sem cobrar. "
    "Nunca cite a linha de Contexto nem diga que a recebe; apenas aja com noção de tempo."
)

ESPERAS = [3, 8, 15]
CODIGOS_TEMPORARIOS = (500, 503, 504)

client = genai.Client()


def montar_instrucoes():
    texto = PERSONALIDADE + "\n\n" + REGRAS_DE_TEMPO
    fatos = memoria.carregar_fatos()
    if fatos:
        lista = "\n".join(f"- {fato}" for fato in fatos)
        texto += "\n\nO que você sabe sobre o Natan:\n" + lista
    return texto


def criar_conversa():
    historico = [
        types.Content(role=m["papel"], parts=[types.Part(text=m["texto"])])
        for m in memoria.carregar_historico()
    ]
    return client.chats.create(
        model=MODELO,
        config=types.GenerateContentConfig(system_instruction=montar_instrucoes()),
        history=historico,
    )


def salvar(conversa):
    mensagens = [
        {
            "papel": conteudo.role,
            "texto": "".join(parte.text or "" for parte in (conteudo.parts or [])),
        }
        for conteudo in conversa.get_history()
    ]
    memoria.salvar_historico(mensagens)


def responder(conversa, mensagem):
    momento = tempo.agora()
    contexto = tempo.montar_contexto(memoria.carregar_ultima_mensagem(), momento)
    texto = f"{contexto}\n{mensagem}"
    for espera in ESPERAS + [None]:
        try:
            resposta = conversa.send_message(texto)
            break
        except errors.APIError as erro:
            if erro.code not in CODIGOS_TEMPORARIOS or espera is None:
                raise
            time.sleep(espera)
    memoria.salvar_ultima_mensagem(momento.isoformat())
    salvar(conversa)
    return resposta.text
