import json
from pathlib import Path

PASTA_DADOS = Path(__file__).parent / "dados"
ARQUIVO_HISTORICO = PASTA_DADOS / "historico.json"
ARQUIVO_FATOS = PASTA_DADOS / "fatos.txt"
LIMITE_MENSAGENS = 30


def _garantir_pasta():
    PASTA_DADOS.mkdir(exist_ok=True)


def carregar_historico():
    if not ARQUIVO_HISTORICO.exists():
        return []
    try:
        mensagens = json.loads(ARQUIVO_HISTORICO.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    mensagens = mensagens[-LIMITE_MENSAGENS:]
    while mensagens and mensagens[0]["papel"] != "user":
        mensagens = mensagens[1:]
    return mensagens


def salvar_historico(mensagens):
    _garantir_pasta()
    ARQUIVO_HISTORICO.write_text(
        json.dumps(mensagens, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def limpar_historico():
    if ARQUIVO_HISTORICO.exists():
        ARQUIVO_HISTORICO.unlink()


def carregar_fatos():
    if not ARQUIVO_FATOS.exists():
        return []
    linhas = ARQUIVO_FATOS.read_text(encoding="utf-8").splitlines()
    return [linha for linha in linhas if linha.strip()]


def adicionar_fato(fato):
    _garantir_pasta()
    with ARQUIVO_FATOS.open("a", encoding="utf-8") as arquivo:
        arquivo.write(fato.strip() + "\n")


def esquecer_fato(numero):
    fatos = carregar_fatos()
    if 1 <= numero <= len(fatos):
        removido = fatos.pop(numero - 1)
        texto = "\n".join(fatos) + ("\n" if fatos else "")
        ARQUIVO_FATOS.write_text(texto, encoding="utf-8")
        return removido
    return None
