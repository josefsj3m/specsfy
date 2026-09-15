"""Contrato de configuração externa e execução do deploy sem perguntas."""

import importlib.util
import os
import pty
import select
import time
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "specsfy-specialist-deploy/assets"
SCAFFOLD = ROOT / "specsfy-specialist-deploy/scripts/scaffold.mjs"


class DeployVaultTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.project = self.base / "projeto com espaço"
        self.project.mkdir()
        (self.project / "SEMVER").write_text("1.2.3\n")
        subprocess.run(["node", str(SCAFFOLD), "--project", str(self.project),
                        "--image", "example/app"], check=True, capture_output=True)
        self.env = {k: v for k, v in os.environ.items()
                    if not k.startswith("ANSIBLE_")}
        self.env["XDG_CONFIG_HOME"] = str(self.base / "config")
        self.env["ANSIBLE_CONFIG"] = str(self.base / "ansible.cfg")
        (self.base / "ansible.cfg").write_text("[defaults]\n")
        self.password = self.base / "senha"
        self.password.write_text("senha-ficticia-do-teste\n")
        self.password.chmod(0o600)
        (self.project / "ansible/inventory.yml").write_text(
            "all:\n  hosts:\n    local:\n      ansible_connection: local\n")
        # O playbook descartável comprova descriptografia sem tocar servidores.
        encrypted = subprocess.run(
            ["ansible-vault", "encrypt_string", "--vault-password-file",
             str(self.password), "--stdin-name", "vault_probe"],
            input="valor-ficticio", text=True, capture_output=True, check=True,
            env=self.env)
        vault = self.project / "ansible/group_vars/all/vault.yml"
        vault.parent.mkdir(parents=True)
        vault.write_text(encrypted.stdout)
        (self.project / "ansible/deploy.yml").write_text(
            "- hosts: all\n  gather_facts: false\n  tasks:\n"
            "    - ansible.builtin.assert:\n"
            "        that: vault_probe == 'valor-ficticio'\n"
            "      no_log: true\n")

    def run_deploy(self, *args, env=None):
        return subprocess.run([str(self.project / "deploy"), *args],
                              cwd=self.project, env=env or self.env,
                              stdin=subprocess.DEVNULL, text=True,
                              capture_output=True, timeout=30)

    def load_helper(self):
        path = self.project / "ansible/vault.py"
        self.assertTrue(path.is_file(), "O scaffold deve gerar o configurador")
        spec = importlib.util.spec_from_file_location("deploy_vault", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_non_interactive_without_source_stops_before_connections(self):
        result = self.run_deploy("run", "--non-interactive")
        self.assertNotEqual(0, result.returncode)
        self.assertIn("configure-vault", result.stderr)
        self.assertNotIn("SERVIDOR", result.stdout)

    def test_non_interactive_decrypts_from_explicit_file(self):
        result = self.run_deploy("run", "--non-interactive",
                                 "--vault-password-file", str(self.password))
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertNotIn("Vault password:", result.stderr)

    def test_non_interactive_respects_environment_and_ansible_config(self):
        for kind in ("environment", "config", "script", "identity"):
            with self.subTest(kind=kind):
                env = self.env.copy()
                (self.base / "ansible.cfg").write_text("[defaults]\n")
                args = []
                if kind == "environment":
                    env["ANSIBLE_VAULT_PASSWORD_FILE"] = str(self.password)
                elif kind == "config":
                    (self.base / "ansible.cfg").write_text(
                        f"[defaults]\nvault_password_file = {self.password}\n")
                elif kind == "script":
                    script = self.base / "cofre"
                    script.write_text("#!/bin/sh\nprintf 'senha-ficticia-do-teste\\n'\n")
                    script.chmod(0o700)
                    env["ANSIBLE_VAULT_PASSWORD_FILE"] = str(script)
                else:
                    args = ["--vault-id", f"producao@{self.password}"]
                result = self.run_deploy("run", "--non-interactive", *args, env=env)
                self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_wrong_password_and_prompt_identity_do_not_fall_back(self):
        self.password.write_text("outra-senha\n")
        for args in (("--vault-password-file", str(self.password)),
                     ("--vault-id", "producao@prompt")):
            with self.subTest(args=args):
                result = self.run_deploy("run", "--non-interactive", *args)
                self.assertNotEqual(0, result.returncode)
                self.assertNotIn("SERVIDOR", result.stdout)
                self.assertNotIn("Vault password:", result.stderr)

    def test_configure_external_password_permissions_and_default_discovery(self):
        helper = self.load_helper()
        with patch.dict(os.environ, self.env, clear=True), \
                patch.object(helper.sys.stdin, "isatty", return_value=True), \
                patch.object(helper.getpass, "getpass", return_value="senha-ficticia-do-teste"):
            helper.configure(self.project, None, False)
            path = helper.default_password_path(self.project)
        self.assertFalse(path.is_relative_to(self.project))
        self.assertEqual(0o600, path.stat().st_mode & 0o777)
        self.assertEqual(0o700, path.parent.stat().st_mode & 0o777)
        result = self.run_deploy("run", "--non-interactive")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_configure_refuses_internal_path_symlink_and_silent_overwrite(self):
        helper = self.load_helper()
        symlink = self.base / "link"
        symlink.symlink_to(self.password)
        with patch.dict(os.environ, self.env, clear=True), \
                patch.object(helper.sys.stdin, "isatty", return_value=True), \
                patch.object(helper.getpass, "getpass", return_value="nova-senha"), \
                patch("builtins.input", return_value="n"):
            for path in (self.project / "senha", symlink):
                with self.subTest(path=path), self.assertRaises(ValueError):
                    helper.configure(self.project, str(path), False)
            helper.configure(self.project, str(self.password), False)
        self.assertEqual("senha-ficticia-do-teste\n", self.password.read_text())

    def test_manual_keeps_prompt_and_refuses_missing_terminal(self):
        result = self.run_deploy("run")
        self.assertNotEqual(0, result.returncode)
        self.assertIn("terminal", result.stderr)
        self.assertNotIn("SERVIDOR", result.stdout)

    def terminal(self, arguments, answers):
        """Exercita o terminal real sem depender de bibliotecas adicionais."""
        pid, descriptor = pty.fork()
        if pid == 0:
            os.chdir(self.project)
            os.execve(str(self.project / "deploy"), ["deploy", *arguments], self.env)
        transcript = b""
        pending = list(answers)
        offset = 0
        deadline = time.monotonic() + 30
        status = None
        try:
            while time.monotonic() < deadline:
                if select.select([descriptor], [], [], 0.1)[0]:
                    try:
                        data = os.read(descriptor, 65536)
                    except OSError:
                        break
                    if not data:
                        break
                    transcript += data
                    if pending and pending[0][0].encode() in transcript[offset:]:
                        _, answer = pending.pop(0)
                        offset = len(transcript)
                        os.write(descriptor, (answer + "\n").encode())
                ended, status = os.waitpid(pid, os.WNOHANG)
                if ended:
                    pid = 0
                    break
            if pid:
                ended, status = os.waitpid(pid, os.WNOHANG)
                if not ended:
                    os.kill(pid, 9)
                    os.waitpid(pid, 0)
                    self.fail("O comando não terminou no terminal de teste")
                pid = 0
            self.assertFalse(pending, transcript.decode(errors="replace"))
            return os.waitstatus_to_exitcode(status), transcript.decode(errors="replace")
        finally:
            os.close(descriptor)
            if pid:
                os.kill(pid, 9)
                os.waitpid(pid, 0)

    def test_manual_deploy_uses_hidden_prompt_even_with_external_configuration(self):
        self.env["ANSIBLE_VAULT_PASSWORD_FILE"] = str(self.base / "inexistente")
        status, output = self.terminal(["run"], [("Senha do Ansible Vault: ", "senha-ficticia-do-teste")])
        self.assertEqual(0, status, output)
        self.assertIn("PLAY RECAP", output)
        self.assertNotIn("senha-ficticia-do-teste", output)
        self.assertNotIn("valor-ficticio", output)

    def test_configure_cli_confirmation_and_secret_not_echoed(self):
        status, output = self.terminal(["configure-vault"], [
            ("Senha atual do Ansible Vault: ", "senha-ficticia-do-teste"),
            ("Repita a senha do Ansible Vault: ", "senha-ficticia-do-teste")])
        self.assertEqual(0, status, output)
        self.assertNotIn("senha-ficticia-do-teste", output)
        result = self.run_deploy("configure-vault", "--show-path")
        self.assertEqual(0, result.returncode, result.stderr)
        path = Path(result.stdout.strip())
        self.assertEqual("senha-ficticia-do-teste\n", path.read_text())
        status, output = self.terminal(["configure-vault"], [("[s/N] ", "n")])
        self.assertEqual(0, status, output)
        self.assertEqual("senha-ficticia-do-teste\n", path.read_text())

    def test_secrets_reuses_source_and_preserves_existing_encrypted_values(self):
        (self.project / "ansible/vault-fields.txt").write_text("vault_probe\nvault_novo\n")
        vault = self.project / "ansible/group_vars/all/vault.yml"
        original = vault.read_text()
        self.env["ANSIBLE_VAULT_PASSWORD_FILE"] = str(self.password)
        status, output = self.terminal(["secrets"], [("Valor de vault_novo: ", "novo-valor-ficticio")])
        self.assertEqual(0, status, output)
        self.assertNotIn("Senha do Ansible Vault:", output)
        self.assertNotIn("novo-valor-ficticio", output)
        self.assertTrue(vault.read_text().startswith(original))
        self.assertIn("vault_novo: !vault", vault.read_text())
        self.assertNotIn("novo-valor-ficticio", vault.read_text())
        helper = self.load_helper()
        with patch.dict(os.environ, self.env, clear=True):
            helper.validate_vault(self.project, ["--vault-password-file", str(self.password)], helper.automated_env())

    def test_configure_rejects_mismatch_and_preserves_password_on_confirmed_failure(self):
        helper = self.load_helper()
        with patch.dict(os.environ, self.env, clear=True), \
                patch.object(helper.sys.stdin, "isatty", return_value=True), \
                patch("builtins.input", return_value="s"), \
                patch.object(helper.getpass, "getpass", side_effect=["nova", "diferente"]):
            with self.assertRaises(ValueError):
                helper.configure(self.project, str(self.password), False)
        self.assertEqual("senha-ficticia-do-teste\n", self.password.read_text())

    def test_explicit_source_overrides_bad_config_and_unknown_flags_fail(self):
        self.env["ANSIBLE_VAULT_PASSWORD_FILE"] = str(self.base / "inexistente")
        result = self.run_deploy("run", "--non-interactive", "--vault-password-file", str(self.password))
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        result = self.run_deploy("run", "--non-interative")
        self.assertEqual(2, result.returncode)
        self.assertNotIn("SERVIDOR", result.stdout)

    def test_project_paths_are_isolated_and_invalid_source_never_uses_local_fallback(self):
        helper = self.load_helper()
        with patch.dict(os.environ, self.env, clear=True), \
                patch.object(helper.sys.stdin, "isatty", return_value=True), \
                patch.object(helper.getpass, "getpass", return_value="senha-ficticia-do-teste"):
            helper.configure(self.project, None, False)
            self.assertNotEqual(helper.default_password_path(self.project),
                                helper.default_password_path(self.base / "outro" / self.project.name))
        self.env["ANSIBLE_VAULT_PASSWORD_FILE"] = str(self.base / "inexistente")
        result = self.run_deploy("run", "--non-interactive")
        self.assertNotEqual(0, result.returncode)
        self.assertNotIn("SERVIDOR", result.stdout)


if __name__ == "__main__":
    unittest.main()
