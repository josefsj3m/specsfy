from pathlib import Path

from behave import given, then, when


ROOT = Path(__file__).resolve().parents[3]


@given("os contratos de setup, testes, tarefas e implementação do Specsfy")
def given_database_contracts(context) -> None:
    context.database_contract = "\n".join(
        (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
        for name in (
            "specsfy-setup",
            "specsfy-05-tasks",
            "specsfy-06-tdd-bdd",
            "specsfy-07-implement",
        )
    )
    context.laravel_contract = (
        ROOT / "specialists" / "specsfy-specialist-laravel" / "SKILL.md"
    ).read_text(encoding="utf-8")


@when("a proteção do banco é inspecionada")
def when_database_protection_is_inspected(context) -> None:
    context.database_protection = " ".join(context.database_contract.split())


@then("o Laravel exige um env de teste com banco separado do desenvolvimento")
def then_laravel_requires_separate_testing_database(context) -> None:
    assert ".env.testing" in context.database_protection
    assert "banco de desenvolvimento" in context.database_protection


@then("a verificação é repetida antes de toda suíte de testes")
def then_database_check_runs_before_every_suite(context) -> None:
    assert "check_database_safety.mjs" in context.database_protection
    assert "antes de executar" in context.database_protection


@then("comandos que zeram ou apagam o banco são ignorados")
def then_destructive_database_commands_are_ignored(context) -> None:
    assert "migrate:fresh" in context.database_protection
    assert "ignore" in context.database_protection.casefold()


@then("RefreshDatabase e DatabaseMigrations não são usados")
def then_destructive_laravel_traits_are_not_used(context) -> None:
    assert "RefreshDatabase" not in context.laravel_contract
    assert "DatabaseMigrations" not in context.laravel_contract
    assert "DatabaseTransactions" in context.laravel_contract
