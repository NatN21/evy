from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

MODELO = "gemini-3.5-flash-lite"
PASTA = Path(__file__).parent
INSTRUCOES = (PASTA / "personalidade.txt").read_text(encoding="utf-8")

client = genai.Client()


def criar_conversa():
    return client.chats.create(
        model=MODELO,
        config=types.GenerateContentConfig(system_instruction=INSTRUCOES),
    )


def responder(conversa, mensagem):
    resposta = conversa.send_message(mensagem)
    return resposta.text
