import memoria


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


FERRAMENTAS = [guardar_fato, esquecer_fato]
