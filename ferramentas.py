from datetime import datetime

import lembretes
import memoria
import tempo


def guardar_fato(fato: str) -> str:
    """Guarda na memória de longo prazo um fato duradouro sobre o Natan.

    Args:
        fato: frase curta e completa por si só. Em eventos futuros, inclua a data exata.
    """
    texto = fato.strip()
    if not texto:
        return "Nada para guardar."
    if texto.lower() in [f.lower() for f in memoria.carregar_fatos()]:
        return "Esse fato já estava guardado."
    memoria.adicionar_fato(texto)
    return "Guardado."


def esquecer_fato(numero: int) -> str:
    """Apaga um fato da memória de longo prazo, a pedido do Natan.

    Args:
        numero: número do fato na lista numerada da memória.
    """
    removido = memoria.esquecer_fato(int(numero))
    if removido:
        return f"Apagado: {removido}"
    return "Não existe fato com esse número."


def criar_lembrete(texto: str, quando: str) -> str:
    """Cria um lembrete para o Natan em uma data e hora específicas.

    Args:
        texto: o que deve ser lembrado, em frase curta.
        quando: data e hora no formato AAAA-MM-DD HH:MM, no horário de Brasília.
    """
    if not texto.strip():
        return "Faltou o texto do lembrete."
    try:
        momento = datetime.strptime(quando.strip().replace("T", " "), "%Y-%m-%d %H:%M")
    except ValueError:
        return "Formato inválido. Use AAAA-MM-DD HH:MM."
    momento = momento.replace(tzinfo=tempo.FUSO)
    if momento < tempo.agora():
        return "Esse horário já passou. Peça ao Natan outro horário."
    novo = lembretes.criar(texto, momento.isoformat())
    return f"Lembrete criado para {lembretes.descrever(novo)} (id {novo['id']})."


def apagar_lembrete(id_lembrete: str) -> str:
    """Apaga um lembrete, a pedido do Natan.

    Args:
        id_lembrete: o id do lembrete, como aparece na lista de lembretes pendentes.
    """
    if lembretes.apagar(id_lembrete.strip()):
        return "Lembrete apagado."
    return "Não existe lembrete com esse id."


FERRAMENTAS = [guardar_fato, esquecer_fato, criar_lembrete, apagar_lembrete]
