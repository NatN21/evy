#!/usr/bin/env python3
"""Cria e valida um backup manual criptografado da Evy.

O backup padrão fica fora do checkout, em /var/backups/evy. O serviço é
parado durante a coleta e iniciado novamente apenas se estava ativo antes.
"""

from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


DESTINO_PADRAO = Path("/var/backups/evy")
SERVICO_PADRAO = "evy"
MODO_ARQUIVO_SEGURO = 0o600
MODO_DIRETORIO_SEGURO = 0o700
NOME_PROCESSOS = re.compile(r"(?:^|\s)(?:\S*/)?(?:servidor|terminal)\.py(?:\s|$)")


class ErroBackup(RuntimeError):
    pass


def mensagem_erro(texto):
    print(f"Erro no backup: {texto}", file=sys.stderr)


def executar(comando, *, cwd=None, entrada=None):
    resultado = subprocess.run(
        comando,
        cwd=cwd,
        input=entrada,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return resultado


def verificar_destino(destino, projeto):
    destino = destino.resolve()
    projeto = projeto.resolve()
    try:
        destino.relative_to(projeto)
    except ValueError:
        pass
    else:
        raise ErroBackup("o destino precisa ficar fora do diretório do projeto")
    if not destino.is_dir():
        raise ErroBackup(
            f"o destino {destino} não existe; prepare-o com proprietário da Evy e modo 700"
        )
    estado = destino.stat()
    if estado.st_uid != os.getuid():
        raise ErroBackup("o destino não pertence ao usuário que executa o backup")
    if estado.st_mode & 0o077:
        raise ErroBackup("o destino precisa ter permissões restritas (modo 700)")
    if not os.access(destino, os.W_OK | os.X_OK):
        raise ErroBackup("o destino não é gravável pelo usuário atual")
    return destino


def estado_git(projeto):
    commit = executar(["git", "rev-parse", "HEAD"], cwd=projeto)
    arvore = executar(["git", "status", "--porcelain"], cwd=projeto)
    if commit.returncode != 0 or arvore.returncode != 0:
        raise ErroBackup("não foi possível identificar o estado do Git")
    return commit.stdout.decode().strip(), ("dirty" if arvore.stdout.strip() else "clean")


def copiar_arvore(origem, destino):
    if not origem.is_dir():
        raise ErroBackup(f"diretório persistente ausente: {origem.name}")
    destino.mkdir(mode=MODO_DIRETORIO_SEGURO)
    os.chmod(destino, MODO_DIRETORIO_SEGURO)
    for item in sorted(origem.rglob("*")):
        relativo = item.relative_to(origem)
        copia = destino / relativo
        if item.is_symlink():
            raise ErroBackup(f"link simbólico não permitido nos dados: {relativo}")
        if item.is_dir():
            copia.mkdir(mode=MODO_DIRETORIO_SEGURO)
            os.chmod(copia, MODO_DIRETORIO_SEGURO)
        elif item.is_file():
            shutil.copyfile(item, copia)
            os.chmod(copia, MODO_ARQUIVO_SEGURO)
        else:
            raise ErroBackup(f"tipo de arquivo não permitido nos dados: {relativo}")


def preparar_arvore(projeto, staging):
    env = projeto / ".env"
    dados = projeto / "dados"
    if not env.is_file():
        raise ErroBackup("arquivo .env ausente")
    if env.is_symlink():
        raise ErroBackup("o arquivo .env não pode ser um link simbólico")
    shutil.copyfile(env, staging / ".env")
    os.chmod(staging / ".env", MODO_ARQUIVO_SEGURO)
    copiar_arvore(dados, staging / "dados")


def sha256(caminho):
    digest = hashlib.sha256()
    with caminho.open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
            digest.update(bloco)
    return digest.hexdigest()


def criar_manifesto(staging, commit, arvore):
    arquivos = []
    for caminho in sorted(staging.rglob("*")):
        if caminho.is_file() and caminho.name != "manifest.json":
            relativo = caminho.relative_to(staging).as_posix()
            arquivos.append(
                {
                    "caminho": relativo,
                    "bytes": caminho.stat().st_size,
                    "sha256": sha256(caminho),
                }
            )
    manifesto = {
        "formato": 1,
        "criado_em": datetime.now(timezone.utc).isoformat(),
        "commit_git": commit,
        "estado_arvore": arvore,
        "arquivos": arquivos,
    }
    arquivo = staging / "manifest.json"
    arquivo.write_text(json.dumps(manifesto, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.chmod(arquivo, MODO_ARQUIVO_SEGURO)


def compactar(staging, destino):
    tar = subprocess.Popen(
        ["tar", "--sort=name", "-C", str(staging), "-cf", "-", "."],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    zstd = subprocess.Popen(
        ["zstd", "-q", "-T0", "-19", "-o", str(destino)],
        stdin=tar.stdout,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    tar.stdout.close()
    zstd.communicate()
    tar.stderr.read()
    retorno_tar = tar.wait()
    if retorno_tar != 0 or zstd.returncode != 0:
        raise ErroBackup("falha ao compactar os arquivos")


def senha(confirmar):
    primeira = getpass.getpass("Senha do backup GPG: ")
    if not primeira:
        raise ErroBackup("a senha não pode ser vazia")
    if confirmar:
        segunda = getpass.getpass("Confirme a senha do backup GPG: ")
        if primeira != segunda:
            raise ErroBackup("as senhas não coincidem")
    return primeira


def gpg_simetrico(operacao, origem, destino, segredo):
    if operacao == "criptografar":
        argumentos = [
            "gpg",
            "--batch",
            "--yes",
            "--pinentry-mode",
            "loopback",
            "--passphrase-fd",
            "0",
            "--symmetric",
            "--cipher-algo",
            "AES256",
            "--output",
            str(destino),
            str(origem),
        ]
    else:
        argumentos = [
            "gpg",
            "--batch",
            "--yes",
            "--pinentry-mode",
            "loopback",
            "--passphrase-fd",
            "0",
            "--decrypt",
            "--output",
            str(destino),
            str(origem),
        ]
    resultado = executar(argumentos, entrada=(segredo + "\n").encode())
    if resultado.returncode != 0:
        raise ErroBackup(f"falha ao {operacao} o arquivo com GPG")


def comandos_servico(servico):
    if os.getenv("EVY_BACKUP_TESTING") == "1":
        comando = os.getenv("EVY_BACKUP_SYSTEMCTL")
        if comando:
            return [comando]
    return ["sudo", "systemctl"]


def estado_servico(servico):
    resultado = executar(comandos_servico(servico) + ["is-active", servico])
    estado = resultado.stdout.decode().strip()
    if estado == "active" and resultado.returncode == 0:
        return True
    if estado in {"inactive", "failed", "deactivating"}:
        return False
    raise ErroBackup("não foi possível determinar com segurança o estado do serviço")


def processos_concorrentes():
    if os.getenv("EVY_BACKUP_TESTING") == "1" and os.getenv("EVY_BACKUP_PS"):
        comando = [os.environ["EVY_BACKUP_PS"]]
    else:
        comando = ["ps", "-eo", "pid=,args="]
    resultado = executar(comando)
    if resultado.returncode != 0:
        raise ErroBackup("não foi possível verificar processos concorrentes")
    encontrados = []
    for linha in resultado.stdout.decode(errors="replace").splitlines():
        partes = linha.strip().split(None, 1)
        try:
            pid = int(partes[0])
        except (IndexError, ValueError):
            continue
        if len(partes) == 2 and pid != os.getpid() and NOME_PROCESSOS.search(partes[1]):
            encontrados.append(partes[1])
    return encontrados


def parar_servico(servico):
    resultado = executar(comandos_servico(servico) + ["stop", servico])
    if resultado.returncode != 0:
        raise ErroBackup("não foi possível parar o serviço")
    if estado_servico(servico):
        raise ErroBackup("o serviço continuou ativo após a parada")
    concorrentes = processos_concorrentes()
    if concorrentes:
        raise ErroBackup("há um servidor ou terminal em execução")


def iniciar_servico(servico):
    resultado = executar(comandos_servico(servico) + ["start", servico])
    if resultado.returncode != 0 or not estado_servico(servico):
        raise ErroBackup("não foi possível restaurar o serviço")


def validar_membros(membros, raiz):
    nomes = set()
    raiz = raiz.resolve()
    for membro in membros:
        nome_texto = membro.name
        while nome_texto.startswith("./"):
            nome_texto = nome_texto[2:]
        if nome_texto == ".":
            nome_texto = ""
        nome = Path(nome_texto)
        if nome.is_absolute() or ".." in nome.parts:
            raise ErroBackup("o arquivo contém um caminho inválido")
        destino = (raiz / nome).resolve()
        try:
            destino.relative_to(raiz)
        except ValueError as erro:
            raise ErroBackup("o arquivo contém um caminho fora da área de restauração") from erro
        if membro.issym() or membro.islnk():
            raise ErroBackup("links simbólicos não são aceitos no arquivo")
        if not membro.isdir() and not membro.isfile():
            raise ErroBackup("tipo de arquivo não permitido no backup")
        if membro.isfile():
            nomes.add(nome.as_posix())
    return nomes


def extrair_e_validar(arquivo, segredo, destino):
    descriptografado = destino / "conteudo.tar.zst"
    tar_path = destino / "conteudo.tar"
    extracao = destino / "restaurado"
    destino.mkdir(mode=MODO_DIRETORIO_SEGURO, parents=True, exist_ok=True)
    extracao.mkdir(mode=MODO_DIRETORIO_SEGURO)
    gpg_simetrico("descriptografar", arquivo, descriptografado, segredo)
    resultado = executar(["zstd", "-q", "-d", "-f", "-o", str(tar_path), str(descriptografado)])
    if resultado.returncode != 0:
        raise ErroBackup("falha ao descompactar o backup")
    import tarfile

    with tarfile.open(tar_path, "r:") as pacote:
        nomes = validar_membros(pacote.getmembers(), extracao)
        pacote.extractall(extracao)
    manifesto_path = extracao / "manifest.json"
    if "manifest.json" not in nomes or not manifesto_path.is_file():
        raise ErroBackup("manifesto ausente no backup")
    try:
        manifesto = json.loads(manifesto_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as erro:
        raise ErroBackup("manifesto inválido") from erro
    if not isinstance(manifesto, dict):
        raise ErroBackup("manifesto inválido")
    itens = manifesto.get("arquivos")
    if not isinstance(itens, list):
        raise ErroBackup("manifesto inválido")
    try:
        esperados = {item["caminho"] for item in itens}
    except (KeyError, TypeError):
        raise ErroBackup("manifesto inválido")
    reais = {nome for nome in nomes if nome != "manifest.json" and not nome.endswith("/")}
    if esperados != reais:
        raise ErroBackup("a lista de arquivos não coincide com o manifesto")
    for item in itens:
        if not isinstance(item, dict) or not isinstance(item.get("caminho"), str):
            raise ErroBackup("manifesto inválido")
        caminho = extracao / item["caminho"]
        if (
            not caminho.is_file()
            or not isinstance(item.get("bytes"), int)
            or not isinstance(item.get("sha256"), str)
            or caminho.stat().st_size != item["bytes"]
            or sha256(caminho) != item["sha256"]
        ):
            raise ErroBackup("a integridade de um arquivo não confere")
    obrigatorios = [
        ".env",
        "dados/historico.json",
        "dados/fatos.txt",
        "dados/estado.json",
        "dados/lembretes.json",
        "dados/inscricoes.json",
        "dados/vapid/private_key.pem",
        "dados/vapid/public_key.pem",
    ]
    if any(not (extracao / caminho).is_file() for caminho in obrigatorios):
        raise ErroBackup("o backup não contém todos os dados obrigatórios")
    os.chmod(extracao / ".env", MODO_ARQUIVO_SEGURO)
    chave = extracao / "dados" / "vapid" / "private_key.pem"
    if chave.exists():
        os.chmod(chave, MODO_ARQUIVO_SEGURO)


def bloquear(destino):
    import fcntl

    arquivo = (destino / ".backup.lock").open("w")
    os.chmod(arquivo.fileno(), MODO_ARQUIVO_SEGURO)
    try:
        fcntl.flock(arquivo.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as erro:
        arquivo.close()
        raise ErroBackup("já existe outro backup em execução") from erro
    return arquivo


def criar_backup(projeto, destino, servico):
    destino = verificar_destino(destino, projeto)
    lock = bloquear(destino)
    ativo = False
    temporario = None
    try:
        ativo = estado_servico(servico)
        if ativo:
            parar_servico(servico)
        elif processos_concorrentes():
            raise ErroBackup("há um servidor ou terminal em execução")
        commit, arvore = estado_git(projeto)
        temporario = Path(tempfile.mkdtemp(prefix=".evy-backup-", dir=destino))
        staging = temporario / "staging"
        staging.mkdir(mode=MODO_DIRETORIO_SEGURO)
        preparar_arvore(projeto, staging)
        criar_manifesto(staging, commit, arvore)
        comprimido = temporario / "backup.tar.zst"
        compactar(staging, comprimido)
        segredo = senha(confirmar=True)
        cifrado = temporario / "backup.tar.zst.gpg"
        gpg_simetrico("criptografar", comprimido, cifrado, segredo)
        extrair_e_validar(cifrado, segredo, temporario / "validacao")
        nome = f"evy-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{commit[:12]}.tar.zst.gpg"
        final = destino / nome
        if final.exists():
            raise ErroBackup("já existe um backup com o mesmo identificador")
        os.chmod(cifrado, MODO_ARQUIVO_SEGURO)
        os.replace(cifrado, final)
        os.chmod(final, MODO_ARQUIVO_SEGURO)
        print(f"Backup validado e publicado: {final}")
        print(f"SHA-256 do arquivo criptografado: {sha256(final)}")
    finally:
        if temporario is not None:
            shutil.rmtree(temporario, ignore_errors=True)
        if ativo:
            try:
                iniciar_servico(servico)
            except ErroBackup as erro:
                mensagem_erro(str(erro))
                raise
        lock.close()


def verificar_backup(arquivo):
    if not arquivo.is_file():
        raise ErroBackup("arquivo de backup não encontrado")
    segredo = senha(confirmar=False)
    with tempfile.TemporaryDirectory(prefix="evy-restauracao-") as temporario:
        extrair_e_validar(arquivo.resolve(), segredo, Path(temporario))
    print("Backup descriptografado, extraído e validado em diretório temporário.")
    print("Os dados originais não foram alterados.")


def argumentos():
    parser = argparse.ArgumentParser(description=__doc__)
    subcomandos = parser.add_subparsers(dest="comando", required=True)
    backup = subcomandos.add_parser("criar", help="cria um backup criptografado")
    backup.add_argument("--project-dir", type=Path, default=Path(__file__).resolve().parent)
    backup.add_argument("--destination", type=Path, default=DESTINO_PADRAO)
    backup.add_argument("--service", default=SERVICO_PADRAO)
    verificar = subcomandos.add_parser("verificar", help="valida um backup sem restaurar dados reais")
    verificar.add_argument("arquivo", type=Path)
    return parser.parse_args()


def main():
    os.umask(0o077)
    args = argumentos()
    try:
        if args.comando == "criar":
            criar_backup(args.project_dir.resolve(), args.destination, args.service)
        else:
            verificar_backup(args.arquivo)
    except (ErroBackup, OSError, ValueError) as erro:
        mensagem_erro(str(erro))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
