import hashlib
import hmac
import json
import os
import secrets
import threading
import time
import uuid

PASTA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dados")
ARQ_DISPOSITIVOS = os.path.join(PASTA, "dispositivos.json")
ARQ_CODIGOS = os.path.join(PASTA, "codigos_pareamento.json")
ALFABETO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
VALIDADE_CODIGO = 300
MAX_FALHAS = 5
JANELA_FALHAS = 600

_trava = threading.Lock()
_falhas = []


class Bloqueado(Exception):
    pass


def _hash(texto):
    return hashlib.sha256(texto.encode()).hexdigest()


def _ler(caminho):
    try:
        with open(caminho, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _gravar(caminho, dados):
    os.makedirs(PASTA, exist_ok=True)
    tmp = caminho + ".tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    os.replace(tmp, caminho)


def criar_codigo():
    codigo = "".join(secrets.choice(ALFABETO) for _ in range(8))
    with _trava:
        agora = time.time()
        codigos = [c for c in _ler(ARQ_CODIGOS) if c["expira"] > agora]
        codigos.append({"hash": _hash(codigo), "expira": agora + VALIDADE_CODIGO})
        _gravar(ARQ_CODIGOS, codigos)
    return f"{codigo[:4]}-{codigo[4:]}"


def parear(codigo, nome):
    codigo = "".join(c for c in codigo.upper() if c in ALFABETO)
    agora = time.time()
    with _trava:
        _falhas[:] = [t for t in _falhas if t > agora - JANELA_FALHAS]
        if len(_falhas) >= MAX_FALHAS:
            raise Bloqueado()
        codigos = [c for c in _ler(ARQ_CODIGOS) if c["expira"] > agora]
        h = _hash(codigo)
        achado = next((c for c in codigos if hmac.compare_digest(c["hash"], h)), None)
        if not achado:
            _falhas.append(agora)
            return None
        codigos.remove(achado)
        _gravar(ARQ_CODIGOS, codigos)
        token = secrets.token_urlsafe(32)
        lista = _ler(ARQ_DISPOSITIVOS)
        lista.append(
            {
                "id": uuid.uuid4().hex[:8],
                "nome": nome,
                "hash": _hash(token),
                "criado": agora,
                "ultimo_uso": agora,
            }
        )
        _gravar(ARQ_DISPOSITIVOS, lista)
        return token


def verificar(token):
    if not token:
        return False
    h = _hash(token)
    with _trava:
        lista = _ler(ARQ_DISPOSITIVOS)
        for d in lista:
            if hmac.compare_digest(d["hash"], h):
                agora = time.time()
                if agora - d["ultimo_uso"] > 3600:
                    d["ultimo_uso"] = agora
                    _gravar(ARQ_DISPOSITIVOS, lista)
                return True
    return False


def listar():
    with _trava:
        return [
            {k: d[k] for k in ("id", "nome", "criado", "ultimo_uso")}
            for d in _ler(ARQ_DISPOSITIVOS)
        ]


def revogar(id_dispositivo):
    with _trava:
        lista = _ler(ARQ_DISPOSITIVOS)
        nova = [d for d in lista if d["id"] != id_dispositivo]
        if len(nova) == len(lista):
            return False
        _gravar(ARQ_DISPOSITIVOS, nova)
        return True
