import memoria
from cerebro import criar_conversa, responder

AJUDA = (
    "Comandos:\n"
    "  /lembrar TEXTO   guarda um fato sobre você\n"
    "  /fatos           lista os fatos guardados\n"
    "  /esquecer N      apaga o fato de número N\n"
    "  /limpar          apaga o histórico da conversa\n"
    "  /ajuda           mostra esta lista\n"
    "  sair             encerra\n"
)


def tratar_comando(entrada, conversa):
    partes = entrada.split(maxsplit=1)
    comando = partes[0].lower()
    argumento = partes[1] if len(partes) > 1 else ""

    if comando == "/ajuda":
        print(AJUDA)
    elif comando == "/lembrar":
        if argumento:
            memoria.adicionar_fato(argumento)
            print("Guardado.\n")
            return criar_conversa()
        print("Use: /lembrar TEXTO\n")
    elif comando == "/fatos":
        fatos = memoria.carregar_fatos()
        if not fatos:
            print("Nenhum fato guardado.")
        for numero, fato in enumerate(fatos, start=1):
            print(f"{numero}. {fato}")
        print()
    elif comando == "/esquecer":
        if argumento.isdigit():
            removido = memoria.esquecer_fato(int(argumento))
            if removido:
                print(f"Esquecido: {removido}\n")
                return criar_conversa()
        print("Use: /esquecer N (número da lista de /fatos)\n")
    elif comando == "/limpar":
        memoria.limpar_historico()
        print("Histórico apagado.\n")
        return criar_conversa()
    else:
        print("Comando desconhecido. Digite /ajuda.\n")
    return conversa


def main():
    conversa = criar_conversa()
    print("Evy no terminal. Digite /ajuda para ver os comandos.\n")
    while True:
        entrada = input("Você: ").strip()
        if not entrada:
            continue
        if entrada.lower() == "sair":
            print("Evy: Até logo!")
            break
        if entrada.startswith("/"):
            conversa = tratar_comando(entrada, conversa)
            continue
        try:
            print("Evy:", responder(conversa, entrada), "\n")
        except Exception as erro:
            print("Erro:", erro, "\n")


if __name__ == "__main__":
    main()
