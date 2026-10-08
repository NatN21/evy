import re
from datetime import datetime
from zoneinfo import ZoneInfo

FUSO = ZoneInfo("America/Sao_Paulo")
DIAS = [
    "segunda-feira",
    "terça-feira",
    "quarta-feira",
    "quinta-feira",
    "sexta-feira",
    "sábado",
    "domingo",
]
PADRAO_CONTEXTO = re.compile(r"^\[Contexto:[^\]]*\]\n?")


def agora():
    return datetime.now(FUSO)


def _plural(n, singular, plural):
    return f"{n} {singular if n == 1 else plural}"


def descrever_intervalo(anterior, atual):
    segundos = int((atual - anterior).total_seconds())
    if segundos < 60:
        return "menos de 1 minuto"
    minutos = segundos // 60
    if minutos < 60:
        return _plural(minutos, "minuto", "minutos")
    horas = minutos // 60
    if horas < 24:
        texto = _plural(horas, "hora", "horas")
        resto = minutos % 60
        if resto:
            texto += " e " + _plural(resto, "minuto", "minutos")
        return texto
    dias = horas // 24
    texto = _plural(dias, "dia", "dias")
    resto = horas % 24
    if resto:
        texto += " e " + _plural(resto, "hora", "horas")
    return texto


def montar_contexto(ultima_iso, momento):
    data = f"{DIAS[momento.weekday()]}, {momento:%d/%m/%Y}, {momento:%H:%M}"
    if ultima_iso:
        anterior = datetime.fromisoformat(ultima_iso)
        passou = descrever_intervalo(anterior, momento)
        ultima = f"A última mensagem do Natan foi há {passou}."
    else:
        ultima = "Esta é a primeira mensagem do Natan."
    return f"[Contexto: {data} (horário de Brasília). {ultima}]"


def remover_contexto(texto):
    return PADRAO_CONTEXTO.sub("", texto)
