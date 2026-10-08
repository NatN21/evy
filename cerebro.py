import time
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

import ferramentas
import lembretes
import memoria
import tempo

load_dotenv()

MODELO = "gemini-3.5-flash-lite"
PASTA = Path(__file__).parent
PERSONALIDADE = (PASTA / "personalidade.txt").read_text(encoding="utf-8")

REGRAS_DE_TEMPO = (
    "Cada mensagem do Natan começa com uma linha [Contexto: ...] que informa a data, "
    "o dia da semana, a hora e há quanto tempo foi a última mensagem dele. "
    "Use isso para se situar no tempo, mas sem comentar o tempo à toa: só fale de data, "
    "hora ou tempo passado quando for relevante para a conversa, por exemplo quando ele "
    "perguntar, quando houver um compromisso próximo ou quando ele voltar depois de "
    "muitas horas ou dias. Quando ele voltar depois de bastante tempo e apenas "
    "cumprimentar, retome com naturalidade o que ele tinha mencionado antes, como "
    "eventos que já aconteceram, oportunidades ou preocupações, perguntando como foi, "
    "sem soar mecânica e sem cobrar. Nunca cite a linha de Contexto nem diga que a recebe."
)

REGRAS_DE_MEMORIA = (
    "Você tem duas ferramentas de memória de longo prazo: guardar_fato e esquecer_fato. "
    "Use guardar_fato quando o Natan pedir para você lembrar de algo e também por "
    "iniciativa própria quando ele contar algo duradouro e útil, como planos, "
    "compromissos, gostos, projetos e decisões. Não guarde conversa trivial nem dados "
    "sensíveis (saúde, dinheiro, senhas, documentos ou segredos de outras pessoas), a "
    "menos que ele peça claramente. Cada fato deve ser uma frase curta e completa por si "
    "só, sem repetir o que já está na memória. Em eventos futuros, escreva a data exata "
    "(por exemplo, domingo, 11/10/2026) e não apenas o dia da semana. Depois de guardar "
    "algo por iniciativa própria, avise de forma breve e natural, no seu jeito de "
    "conversar e sem tom de nota de sistema, o que guardou. Use "
    "esquecer_fato quando ele pedir para apagar algo, com o número do fato na lista. "
    "Nunca diga que guardou ou apagou algo sem ter usado a ferramenta."
)

REGRAS_DE_LEMBRETES = (
    "Você tem duas ferramentas de lembretes: criar_lembrete e apagar_lembrete. "
    "Use criar_lembrete quando o Natan pedir para ser lembrado de algo em um dia e hora. "
    "Converta expressões como amanhã, daqui a 10 minutos ou sexta usando a data e a hora "
    "do Contexto da mensagem atual. Se faltar o dia ou a hora, pergunte antes de criar. "
    "Depois de criar, confirme de forma breve e natural, citando o dia da semana, a data "
    "e a hora. Use apagar_lembrete, com o id da lista de lembretes pendentes, quando ele "
    "pedir para cancelar um. Lembretes marcados como JÁ PASSOU ainda não foram avisados, "
    "porque as notificações no celular ainda não existem; mencione-os se fizer sentido. "
    "Nunca diga que criou ou apagou um lembrete sem ter usado a ferramenta."
)

ESPERAS = [3, 8, 15]
CODIGOS_TEMPORARIOS = (500, 503, 504)

client = genai.Client()


def montar_instrucoes():
    texto = "\n\n".join(
        [PERSONALIDADE, REGRAS_DE_TEMPO, REGRAS_DE_MEMORIA, REGRAS_DE_LEMBRETES]
    )
    fatos = memoria.carregar_fatos()
    if fatos:
        lista = "\n".join(f"{n}. {fato}" for n, fato in enumerate(fatos, start=1))
        texto += "\n\nMemória de longo prazo sobre o Natan (fatos numerados):\n" + lista
    else:
        texto += "\n\nA memória de longo prazo ainda está vazia."
    texto += "\n\n" + lembretes.resumo()
    return texto


def criar_conversa():
    historico = [
        types.Content(role=m["papel"], parts=[types.Part(text=m["texto"])])
        for m in memoria.carregar_historico()
    ]
    return client.chats.create(
        model=MODELO,
        config=types.GenerateContentConfig(
            system_instruction=montar_instrucoes(),
            tools=ferramentas.FERRAMENTAS,
        ),
        history=historico,
    )


def salvar(conversa):
    mensagens = []
    for conteudo in conversa.get_history():
        texto = "".join(parte.text or "" for parte in (conteudo.parts or []))
        if not texto.strip():
            continue
        if mensagens and mensagens[-1]["papel"] == conteudo.role:
            mensagens[-1]["texto"] += "\n" + texto
        else:
            mensagens.append({"papel": conteudo.role, "texto": texto})
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
