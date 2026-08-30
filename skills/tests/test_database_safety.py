from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "specsfy-setup" / "scripts" / "check_database_safety.mjs"


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def run_checker(project: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["node", str(CHECKER), "--project", str(project), "--json", *arguments],
        text=True,
        capture_output=True,
        check=False,
    )


class DatabaseSafetyTests(unittest.TestCase):
    def laravel_project(self, root: Path) -> None:
        write(root / "artisan", "#!/usr/bin/env php\n")
        write(
            root / ".env",
            "APP_ENV=local\nDB_CONNECTION=mysql\nDB_HOST=127.0.0.1\n"
            "DB_PORT=3306\nDB_DATABASE=produto_dev\nDB_USERNAME=dev\n"
            "DB_PASSWORD=segredo-dev\n",
        )

    def test_requires_env_testing_for_laravel(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            self.laravel_project(project)

            result = run_checker(project)

            self.assertEqual(1, result.returncode)
            payload = json.loads(result.stdout)
            self.assertEqual("pending", payload["status"])
            self.assertIn(".env.testing", " ".join(payload["errors"]))
            self.assertNotIn("segredo-dev", result.stdout)

    def test_rejects_testing_env_that_targets_development_database(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            self.laravel_project(project)
            write(
                project / ".env.testing",
                "APP_ENV=testing\nDB_CONNECTION=mysql\nDB_HOST=127.0.0.1\n"
                "DB_PORT=3306\nDB_DATABASE=produto_dev\n",
            )

            result = run_checker(project)

            self.assertEqual(1, result.returncode)
            self.assertIn("banco de desenvolvimento", result.stdout)

    def test_compares_inherited_connection_with_development_database(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            self.laravel_project(project)
            write(
                project / ".env.testing",
                "APP_ENV=testing\nDB_DATABASE=produto_dev\n",
            )

            result = run_checker(project)

            self.assertEqual(1, result.returncode)
            self.assertIn("banco de desenvolvimento", result.stdout)

    def test_rejects_testing_env_that_inherits_database_name(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            self.laravel_project(project)
            write(project / ".env.testing", "APP_ENV=testing\n")

            result = run_checker(project)

            self.assertEqual(1, result.returncode)
            self.assertIn("sem herdar o .env", result.stdout)

    def test_accepts_explicit_separate_testing_database(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            self.laravel_project(project)
            write(
                project / ".env.testing",
                "APP_ENV=testing\nDB_CONNECTION=mysql\nDB_HOST=127.0.0.1\n"
                "DB_PORT=3306\nDB_DATABASE=produto_test\n",
            )

            result = run_checker(project)

            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertEqual("safe", json.loads(result.stdout)["status"])

    def test_ignores_destructive_database_command_even_with_test_database(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            self.laravel_project(project)
            write(
                project / ".env.testing",
                "APP_ENV=testing\nDB_CONNECTION=mysql\nDB_HOST=127.0.0.1\n"
                "DB_PORT=3306\nDB_DATABASE=produto_test\n",
            )

            result = run_checker(
                project,
                "--command",
                "php artisan migrate:fresh --env=testing",
            )

            self.assertEqual(3, result.returncode)
            self.assertEqual("ignored", json.loads(result.stdout)["status"])

    def test_ignores_suite_that_uses_refresh_database(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            self.laravel_project(project)
            write(
                project / ".env.testing",
                "APP_ENV=testing\nDB_CONNECTION=mysql\nDB_HOST=127.0.0.1\n"
                "DB_PORT=3306\nDB_DATABASE=produto_test\n",
            )
            write(
                project / "tests/Pest.php",
                "<?php\nuse Illuminate\\Foundation\\Testing\\RefreshDatabase;\n",
            )

            result = run_checker(project, "--command", "php artisan test")

            self.assertEqual(3, result.returncode)
            self.assertIn("RefreshDatabase", result.stdout)

    def test_ignores_destructive_composer_test_alias(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            self.laravel_project(project)
            write(
                project / ".env.testing",
                "APP_ENV=testing\nDB_DATABASE=produto_test\n",
            )
            write(
                project / "composer.json",
                '{"scripts":{"test":"php artisan migrate:fresh && php artisan test"}}',
            )

            result = run_checker(project, "--command", "composer test")

            self.assertEqual(3, result.returncode)
            self.assertIn("script test", result.stdout)

    def test_allows_safe_up_even_when_down_drops_created_table(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            self.laravel_project(project)
            write(project / ".env.testing", "APP_ENV=testing\nDB_DATABASE=produto_test\n")
            write(
                project / "database/migrations/create_items.php",
                "<?php\npublic function up(): void { Schema::create('items'); }\n"
                "public function down(): void { Schema::dropIfExists('items'); }\n",
            )

            result = run_checker(project, "--command", "php artisan migrate --env=testing")

            self.assertEqual(0, result.returncode, result.stdout)

    def test_ignores_destructive_up_migration(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            self.laravel_project(project)
            write(project / ".env.testing", "APP_ENV=testing\nDB_DATABASE=produto_test\n")
            write(
                project / "database/migrations/remove_items.php",
                "<?php\npublic function up(): void { Schema::dropIfExists('items'); }\n"
                "public function down(): void {}\n",
            )

            result = run_checker(project, "--command", "php artisan migrate --env=testing")

            self.assertEqual(3, result.returncode)

    def test_core_skills_apply_the_same_database_protection(self) -> None:
        sources = {
            name: (ROOT / name / "SKILL.md").read_text(encoding="utf-8")
            for name in (
                "specsfy-setup",
                "specsfy-05-tasks",
                "specsfy-06-tdd-bdd",
                "specsfy-07-implement",
            )
        }
        specialist = (
            ROOT.parent / "specialists" / "specsfy-specialist-laravel" / "SKILL.md"
        ).read_text(encoding="utf-8")

        for name, content in sources.items():
            with self.subTest(skill=name):
                self.assertIn("check_database_safety.mjs", content)
        self.assertIn(".env.testing", specialist)
        self.assertIn("DatabaseTransactions", specialist)
        self.assertNotIn("RefreshDatabase", specialist)


if __name__ == "__main__":
    unittest.main()
