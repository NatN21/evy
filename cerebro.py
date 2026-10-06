from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types

import memoria

load_dotenv()

MODELO = "gemini-3.5-flash-lite"
PASTA = Path(__file__).parent
PERSONALIDADE = (PASTA / "personalidade.txt").read_text(encoding="utf-8")

client = genai.Client()


def montar_instrucoes():
    fatos = memoria.carregar_fatos()
    if not fatos:
        return PERSONALIDADE
    lista = "\n".join(f"- {fato}" for fato in fatos)
    return PERSONALIDADE + "\n\nO que você sabe sobre o Natan:\n" + lista


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
    resposta = conversa.send_message(mensagem)
    salvar(conversa)
    return resposta.text
