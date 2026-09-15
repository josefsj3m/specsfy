"""Confere o manual contra a interface publicada nos assets do especialista."""

import ast
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DeployVaultDocumentationTests(unittest.TestCase):
    def test_every_vault_option_and_action_has_documented_examples(self):
        source = ROOT / "specialists/specsfy-specialist-deploy/assets/vault.py"
        tree = ast.parse(source.read_text())
        guide = (ROOT / "docs/user/deploy-vault.md").read_text()
        options = {node.args[0].value for node in ast.walk(tree)
                   if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                   and node.func.attr == "add_argument" and node.args
                   and isinstance(node.args[0], ast.Constant)
                   and str(node.args[0].value).startswith("--")}
        for option in options:
            self.assertIn(f"`{option}", guide, option)
        blocks = re.findall(r"```bash\n(.*?)```", guide, re.DOTALL)
        for command in ("configure-vault", "run", "secrets"):
            self.assertIn(f"### Comando {command}", guide)
            self.assertGreaterEqual(sum(f"./deploy {command}" in block for block in blocks), 5)

    def test_both_specialists_and_technical_guide_describe_agent_execution(self):
        for relative in ("specialists/specsfy-specialist-deploy/SKILL.md",
                         "specialists/specsfy-specialist-ansible/SKILL.md",
                         "docs/develop/skills.md"):
            content = (ROOT / relative).read_text()
            self.assertIn("--non-interactive", content, relative)
            self.assertIn("configure-vault", content, relative)


if __name__ == "__main__":
    unittest.main()
