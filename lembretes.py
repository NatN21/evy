import json
import uuid
from datetime import datetime, timedelta
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
        "avisado": False,
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
    todos = listar()
    if not todos:
        return "Não há lembretes."
    agora = tempo.agora()
    linhas = []
    for lembrete in todos:
        if lembrete.get("avisado"):
            marca = " (JÁ AVISADO)"
        elif datetime.fromisoformat(lembrete["quando"]) < agora:
            marca = " (JÁ PASSOU, AINDA NÃO AVISADO)"
        else:
            marca = ""
        linhas.append(
            f"- [{lembrete['id']}] {descrever(lembrete)}{marca}: {lembrete['texto']}"
        )
    return "Lembretes (os avisos chegam ao celular na hora marcada):\n" + "\n".join(
        linhas
    )


def para_painel():
    agora = tempo.agora()
    itens = []
    for lembrete in listar():
        passou = datetime.fromisoformat(lembrete["quando"]) < agora
        avisado = bool(lembrete.get("avisado"))
        itens.append(
            {
                "id": lembrete["id"],
                "texto": lembrete["texto"],
                "descricao": descrever(lembrete) + (" ✓ avisado" if avisado else ""),
                "vencido": passou and not avisado,
            }
        )
    return itens


def pendentes_para_avisar():
    agora = tempo.agora()
    return [
        l
        for l in listar()
        if not l.get("avisado") and datetime.fromisoformat(l["quando"]) <= agora
    ]


def marcar_avisado(id_lembrete):
    lista = _carregar()
    for lembrete in lista:
        if lembrete["id"] == id_lembrete:
            lembrete["avisado"] = True
    _salvar(lista)


def atraso_em_minutos(lembrete):
    quando = datetime.fromisoformat(lembrete["quando"])
    return int((tempo.agora() - quando).total_seconds() // 60)


def limpar_antigos(dias=2):
    limite = tempo.agora() - timedelta(days=dias)
    lista = _carregar()
    restantes = [
        l
        for l in lista
        if not (l.get("avisado") and datetime.fromisoformat(l["quando"]) < limite)
    ]
    if len(restantes) != len(lista):
        _salvar(restantes)
