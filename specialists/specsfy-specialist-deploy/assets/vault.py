#!/usr/bin/env python3
"""Configura a senha externa e executa Ansible com ou sem terminal interativo."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import getpass
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
import warnings


def default_password_path(project: Path) -> Path:
    """Isola checkouts pela raiz real, inclusive projetos com nomes iguais."""
    project = project.resolve()
    name = re.sub(r"[^a-zA-Z0-9_-]", "-", project.name) or "projeto"
    digest = hashlib.sha256(os.fsencode(project)).hexdigest()[:16]
    base = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
    if not base.is_absolute():
        raise ValueError("XDG_CONFIG_HOME deve ser um caminho absoluto.")
    return base / "specsfy" / "vault" / f"{name}-{digest}" / "password"


def hidden_input(prompt: str) -> str:
    """Recusa o fallback do getpass que poderia ecoar a entrada."""
    if not sys.stdin.isatty():
        raise ValueError("Esta ação exige um terminal interativo.")
    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)
        value = getpass.getpass(prompt)
    if not value or "\n" in value or "\r" in value or "\0" in value:
        raise ValueError("Informe um valor não vazio em uma única linha.")
    return value


def external_path(project: Path, value: str | None) -> Path:
    """Recusa destinos internos ao worktree e links simbólicos no caminho."""
    path = Path(value).expanduser().absolute() if value else default_password_path(project)
    for part in (path, *path.parents):
        if part.is_symlink():
            raise ValueError("A senha externa não pode usar links simbólicos.")
    root = subprocess.run(["git", "-C", str(project), "rev-parse", "--show-toplevel"],
                          capture_output=True, text=True, check=False)
    repository = Path(root.stdout.strip()).resolve() if root.returncode == 0 else project.resolve()
    if path.resolve().is_relative_to(repository):
        raise ValueError("Salve a senha fora do repositório do projeto.")
    if path.exists() and (not path.is_file() or path.stat().st_uid != os.getuid()):
        raise ValueError("O destino deve ser um arquivo regular do seu usuário.")
    return path


def configure(project: Path, value: str | None, show_path: bool) -> None:
    """Grava por substituição atômica; só sobrescreve após confirmação humana."""
    path = external_path(project, value)
    if show_path:
        print(path)
        return
    if not sys.stdin.isatty():
        raise ValueError("Execute ./deploy configure-vault em um terminal interativo.")
    if path.exists() and input(f"Substituir a senha em {path}? [s/N] ").strip().lower() != "s":
        print("Configuração existente preservada.")
        return
    password = hidden_input("Senha atual do Ansible Vault: ")
    if hidden_input("Repita a senha do Ansible Vault: ") != password:
        raise ValueError("As senhas não coincidem; nenhum arquivo foi alterado.")
    # As permissões são aplicadas antes de qualquer byte da senha ser gravado.
    previous_umask = os.umask(0o077)
    temporary = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if path.parent.stat().st_uid != os.getuid():
            raise ValueError("A pasta de destino deve pertencer ao seu usuário.")
        path.parent.chmod(0o700)
        descriptor, temporary = tempfile.mkstemp(prefix=".vault-", dir=path.parent)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            os.fchmod(stream.fileno(), 0o600)
            stream.write(password + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        os.umask(previous_umask)
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)
    print(f"Senha configurada fora do repositório: {path}")
    if value:
        print("Use esse caminho em --vault-password-file ou ANSIBLE_VAULT_PASSWORD_FILE.")


def native_sources() -> tuple[str | None, list[str]]:
    """Consulta a resolução oficial de ambiente e ansible.cfg, sem exibir seu dump."""
    result = subprocess.run(["ansible-config", "dump", "--format", "json"],
                            capture_output=True, text=True, check=False,
                            stdin=subprocess.DEVNULL, timeout=30, start_new_session=True)
    if result.returncode:
        raise ValueError("Não foi possível ler a configuração do Ansible.")
    config = {entry.get("name", entry.get("option")): entry.get("value")
              for entry in json.loads(result.stdout)}
    return config.get("DEFAULT_VAULT_PASSWORD_FILE"), config.get("DEFAULT_VAULT_IDENTITY_LIST") or []


def source_arguments(project: Path, password_file: str | None, identities: list[str]) -> list[str]:
    """Prioriza fonte explícita, configuração nativa e cadastro local, nessa ordem."""
    if password_file or identities:
        file, ids = password_file, identities
    else:
        file, ids = native_sources()
    args = ["--vault-password-file", file] if file else []
    for identity in ids:
        source = identity.rsplit("@", 1)[-1]
        if source == "prompt":
            raise ValueError("Vault ID com prompt não é aceito neste modo; configure uma fonte externa.")
        args.extend(["--vault-id", identity])
    if not args:
        path = default_password_path(project)
        if not path.exists():
            raise ValueError("Fonte de senha ausente. Execute ./deploy configure-vault no terminal.")
        external_path(project, str(path))
        info = path.stat()
        if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077:
            raise ValueError("O arquivo da senha local deve ter permissão 600.")
        args = ["--vault-password-file", str(path)]
    return args


def automated_env() -> dict[str, str]:
    """Desativa perguntas nativas; o SSH precisa estar pronto para autenticar por chave."""
    env = os.environ.copy()
    env.update(ANSIBLE_ASK_PASS="False", ANSIBLE_BECOME_ASK_PASS="False",
               ANSIBLE_ASK_VAULT_PASS="False")
    # A fonte já foi resolvida. Evita fontes adicionais e prompts herdados.
    env["ANSIBLE_VAULT_PASSWORD_FILE"] = ""
    env["ANSIBLE_VAULT_IDENTITY_LIST"] = ""
    env["ANSIBLE_SSH_ARGS"] = "-o BatchMode=yes " + env.get("ANSIBLE_SSH_ARGS", "")
    return env


def execute(command: list[str], env: dict[str, str], quiet: bool = False) -> None:
    """Executa sem shell ou terminal controlador e propaga falhas sem vazar segredos."""
    result = subprocess.run(command, env=env, stdin=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL if quiet else None,
                            stderr=subprocess.PIPE if quiet else None,
                            start_new_session=True, check=False)
    if result.returncode:
        if quiet:
            raise ValueError("Falha ao abrir o Vault ou carregar o inventário; confira a fonte da senha e a configuração do Ansible.")
        raise ValueError(f"A etapa {Path(command[0]).name} terminou com código {result.returncode}.")


@contextmanager
def credentials(project: Path, password_file: str | None, identities: list[str], manual: bool):
    """Mantém a senha manual em arquivo temporário 600 apenas durante a execução."""
    if not manual:
        yield source_arguments(project, password_file, identities)
        return
    password = hidden_input("Senha do Ansible Vault: ")
    with tempfile.TemporaryDirectory(prefix="specsfy-vault-") as directory:
        path = Path(directory) / "password"
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(password + "\n")
        yield ["--vault-password-file", str(path)]


def run_deploy(project: Path, args: argparse.Namespace) -> None:
    """Valida a leitura local antes das conexões e do playbook de deploy."""
    inventory = os.environ.get("ANSIBLE_INVENTORY", str(project / "ansible/inventory.yml"))
    if not Path(inventory).is_file():
        raise ValueError(f"Inventário ausente: {inventory}")
    if not args.non_interactive and (args.vault_password_file or args.vault_id):
        raise ValueError("Use --non-interactive ao informar uma fonte externa para run.")
    with credentials(project, args.vault_password_file, args.vault_id, not args.non_interactive) as source:
        env = automated_env()
        validate_vault(project, source, env)
        execute(["ansible-inventory", "-i", inventory, "--list", *source], env, quiet=True)
        execute([sys.executable, str(project / "ansible/check-hosts.py"),
                 "--inventory", inventory, *source], env)
        execute(["ansible-playbook", "-i", inventory,
                 str(project / "ansible/deploy.yml"), *source], env)


def validate_vault(project: Path, source: list[str], env: dict[str, str]) -> None:
    """Força a descriptografia local; o inventário sozinho mantém strings preguiçosas."""
    vault = project / "ansible/group_vars/all/vault.yml"
    if not vault.is_file():
        raise ValueError("Vault ausente. Cadastre os valores com ./deploy secrets no terminal.")
    play = [{"hosts": "localhost", "connection": "local", "gather_facts": False,
             "tasks": [
                 {"ansible.builtin.include_vars": {"file": str(vault), "name": "specsfy_vault"},
                  "no_log": True},
                 {"ansible.builtin.assert": {"that": [
                     "(specsfy_vault | to_json(vault_to_text=True)) | length > 2"]},
                  "no_log": True}]}]
    with tempfile.TemporaryDirectory(prefix="specsfy-vault-check-") as directory:
        check = Path(directory) / "check.json"
        check.write_text(json.dumps(play), encoding="utf-8")
        execute(["ansible-playbook", "-i", "localhost,", str(check), *source], env, quiet=True)


def create_secrets(project: Path, args: argparse.Namespace) -> None:
    """Acrescenta somente campos ausentes, com publicação atômica do YAML criptografado."""
    base = project / "ansible"
    vault = base / "group_vars/all/vault.yml"
    original = vault.read_text(encoding="utf-8") if vault.exists() else ""
    fields = (base / "vault-fields.txt").read_text(encoding="utf-8").splitlines()
    if any(not re.fullmatch(r"vault_[a-z0-9_]+", field) for field in fields):
        raise ValueError("Nome de variável inválido em vault-fields.txt.")
    missing = [field for field in dict.fromkeys(fields)
               if not re.search(rf"^{re.escape(field)}:", original, re.MULTILINE)]
    if not missing:
        print(f"Vault já contém todos os campos: {vault}")
        return
    # Os valores da aplicação continuam sendo cadastrados por uma pessoa.
    if not sys.stdin.isatty():
        raise ValueError("Cadastre os campos ausentes com ./deploy secrets em um terminal interativo.")
    manual = not (args.vault_password_file or args.vault_id)
    if manual:
        file, ids = native_sources()
        manual = not (file or ids or default_password_path(project).exists())
    with credentials(project, args.vault_password_file, args.vault_id, manual) as source:
        env = automated_env()
        if original.strip():
            validate_vault(project, source, env)
        updated = original
        for field in missing:
            value = hidden_input(f"Valor de {field}: ")
            result = subprocess.run(["ansible-vault", "encrypt_string", *source,
                                     "--stdin-name", field], input=value, text=True,
                                    capture_output=True, env=env, check=False,
                                    start_new_session=True)
            if result.returncode:
                raise ValueError("Não foi possível criptografar o campo; o Vault foi preservado.")
            updated += ("\n" if updated and not updated.endswith("\n") else "") + result.stdout + "\n"
        vault.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix=".vault-", dir=vault.parent)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                stream.write(updated)
            os.replace(temporary, vault)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    print(f"Vault atualizado: {vault}")


def main() -> int:
    """Expõe somente caminhos e opções, sem aceitar a senha como argumento."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    configure_parser = commands.add_parser("configure-vault", help="Configurar senha fora do Git")
    configure_parser.add_argument("--vault-password-file", help="Arquivo externo de destino")
    configure_parser.add_argument("--show-path", action="store_true", help="Consultar caminho sem ler a senha")
    for action in ("run", "secrets"):
        command = commands.add_parser(action)
        command.add_argument("--vault-password-file", help="Arquivo ou script que fornece a senha")
        command.add_argument("--vault-id", action="append", default=[], help="Identificador@fonte; pode repetir")
        if action == "run":
            command.add_argument("--non-interactive", action="store_true", help="Executar sem perguntas")
    args = parser.parse_args()
    project = Path(__file__).resolve().parents[1]
    try:
        if args.action == "configure-vault":
            configure(project, args.vault_password_file, args.show_path)
        elif args.action == "run":
            run_deploy(project, args)
        else:
            create_secrets(project, args)
    except (ValueError, OSError, EOFError, getpass.GetPassWarning, subprocess.TimeoutExpired):
        # Mensagens de subprocessos/cofres podem conter valores; não as encaminha.
        error = sys.exc_info()[1]
        print(str(error) if isinstance(error, ValueError) else
              "Não foi possível concluir a ação; confira terminal, arquivos e ferramentas instaladas.", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Operação cancelada.", file=sys.stderr)
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
