from cerebro import criar_conversa, responder


def main():
    conversa = criar_conversa()
    print("Evy no terminal. Digite 'sair' para encerrar.\n")
    while True:
        mensagem = input("Você: ").strip()
        if not mensagem:
            continue
        if mensagem.lower() == "sair":
            print("Evy: Até logo!")
            break
        try:
            print("Evy:", responder(conversa, mensagem), "\n")
        except Exception as erro:
            print("Erro:", erro, "\n")


if __name__ == "__main__":
    main()
