import json
import uuid
from datetime import datetime
from pathlib import Path

import tempo

PASTA_DADOS = Path(__file__).parent / "dados"
ARQUIVO = PASTA_DADOS / "lembretes.json"


def _carregar():
    if not ARQUIVO.exists():
        return []
    try:
        return json.loads(ARQUIVO.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def _salvar(lista):
    PASTA_DADOS.mkdir(exist_ok=True)
    ARQUIVO.write_text(
        json.dumps(lista, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def listar():
    return sorted(_carregar(), key=lambda l: datetime.fromisoformat(l["quando"]))


def criar(texto, quando_iso):
    lista = _carregar()
    novo = {
        "id": uuid.uuid4().hex[:6],
        "texto": texto.strip(),
        "quando": quando_iso,
        "criado": tempo.agora().isoformat(),
    }
    lista.append(novo)
    _salvar(lista)
    return novo


def apagar(id_lembrete):
    lista = _carregar()
    restantes = [l for l in lista if l["id"] != id_lembrete]
    if len(restantes) == len(lista):
        return False
    _salvar(restantes)
    return True


def descrever(lembrete):
    quando = datetime.fromisoformat(lembrete["quando"])
    return f"{tempo.DIAS[quando.weekday()]}, {quando:%d/%m/%Y} às {quando:%H:%M}"


def resumo():
    pendentes = listar()
    if not pendentes:
        return "Não há lembretes pendentes."
    agora = tempo.agora()
    linhas = []
    for lembrete in pendentes:
        passou = datetime.fromisoformat(lembrete["quando"]) < agora
        marca = " (JÁ PASSOU)" if passou else ""
        linhas.append(
            f"- [{lembrete['id']}] {descrever(lembrete)}{marca}: {lembrete['texto']}"
        )
    return "Lembretes pendentes:\n" + "\n".join(linhas)


def para_painel():
    agora = tempo.agora()
    return [
        {
            "id": l["id"],
            "texto": l["texto"],
            "descricao": descrever(l),
            "vencido": datetime.fromisoformat(l["quando"]) < agora,
        }
        for l in listar()
    ]
