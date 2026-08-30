from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "cli" / "bin" / "specsfy"


class CliTestRunnerContractTests(unittest.TestCase):
    def test_detects_the_laravel_pest_command_in_a_consumer_project(self) -> None:
        with (
            tempfile.TemporaryDirectory() as directory,
            tempfile.TemporaryDirectory() as commands,
        ):
            project = Path(directory).resolve()
            (project / "artisan").write_text("#!/usr/bin/env php\n", encoding="utf-8")
            (project / "composer.json").write_text(
                json.dumps({"require-dev": {"pestphp/pest": "^4.7"}}),
                encoding="utf-8",
            )
            (project / ".env").write_text(
                "APP_ENV=local\nDB_CONNECTION=mysql\nDB_DATABASE=produto_dev\n",
                encoding="utf-8",
            )
            (project / ".env.testing").write_text(
                "APP_ENV=testing\nDB_DATABASE=produto_test\n",
                encoding="utf-8",
            )
            php = Path(commands) / "php"
            php.write_text(
                "#!/bin/sh\n"
                'test "$1" = "artisan"\n'
                'test "$2" = "test"\n'
                "printf '1 passed\\n'\n",
                encoding="utf-8",
            )
            php.chmod(0o755)
            environment = os.environ.copy()
            environment["PATH"] = f"{commands}:{environment.get('PATH', '')}"

            result = subprocess.run(
                [str(CLI), "test", "--project", str(project)],
                text=True,
                capture_output=True,
                env=environment,
                check=False,
            )

            self.assertEqual(0, result.returncode, result.stderr)
            self.assertIn("1 passed", result.stdout)


if __name__ == "__main__":
    unittest.main()
