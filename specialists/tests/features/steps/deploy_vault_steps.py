"""Executa os mesmos contratos observáveis usados na suíte focal de Vault."""

import importlib.util
from pathlib import Path
import unittest

from behave import then


def run_case(name):
    path = Path(__file__).resolve().parents[2] / "test_deploy_vault.py"
    spec = importlib.util.spec_from_file_location("deploy_vault_contract", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = unittest.TestResult()
    module.DeployVaultTests(name).run(result)
    assert result.wasSuccessful(), result.errors + result.failures


@then("o deploy manual usa entrada oculta mesmo com uma fonte externa")
def manual(context):
    run_case("test_manual_deploy_uses_hidden_prompt_even_with_external_configuration")


@then("o configurador grava fora do projeto e pede confirmação para substituir")
def configure(context):
    run_case("test_configure_cli_confirmation_and_secret_not_echoed")
    run_case("test_configure_external_password_permissions_and_default_discovery")


@then("o deploy aceita arquivo, script, configuração nativa e identidade")
def automated(context):
    run_case("test_non_interactive_respects_environment_and_ansible_config")


@then("uma senha incorreta ou identidade com prompt interrompe o deploy")
def invalid(context):
    run_case("test_wrong_password_and_prompt_identity_do_not_fall_back")
