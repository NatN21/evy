import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

MODELO = "gemini-3.5-flash-lite"
INSTRUCOES = (
    "Você é a Evy, assistente pessoal do Natan. "
    "Responda sempre em português do Brasil, de forma clara e calorosa."
)

client = genai.Client()


def criar_conversa():
    return client.chats.create(
        model=MODELO,
        config=types.GenerateContentConfig(system_instruction=INSTRUCOES),
    )


def responder(conversa, mensagem):
    resposta = conversa.send_message(mensagem)
    return resposta.text
