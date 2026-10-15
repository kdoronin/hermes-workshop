"""Portable hook catalog checks; no scheduler or external accounts."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest

from test_repository import validator


class HookCatalogTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        catalog = {"schema_version": 1, "installation_policy": "explicit-selection-only", "modules": [
            {"id": "demo", "file": "demo.md", "requires": [], "default_selected": False}
        ]}
        (self.root / "modules.json").write_text(json.dumps(catalog))
        (self.root / "README.md").write_text("[Demo](demo.md)\n")
        (self.root / "demo.md").write_text("# Demo\n")
        self.hooks = {"schema_version": 1, "installation_policy": "explicit-selection-only", "hooks": []}
        for domain in ("personal", "work"):
            for cadence in ("daily", "weekly", "calendar-event"):
                self.hooks["hooks"].append({
                    "id": domain + "-" + cadence, "domain": domain, "cadence": cadence,
                    "title": "Example", "purpose": "Useful result", "prompt_template": "Use approved context.",
                    "requires": ["calendar"] if cadence == "calendar-event" else [],
                    "default_selected": False,
                })

    def save(self):
        (self.root / "hooks.json").write_text(json.dumps(self.hooks))

    def test_explicit_selection(self):
        self.save()
        self.assertTrue(validator.validate(self.root)["ok"])
        self.hooks["hooks"][0]["default_selected"] = True
        self.save()
        self.assertFalse(validator.validate(self.root)["ok"])

    def test_schema_and_coverage(self):
        original = copy.deepcopy(self.hooks)
        mutations = {
            "bad-policy": lambda c: c.update(installation_policy="automatic"),
            "bad-version": lambda c: c.update(schema_version=99),
            "missing-group": lambda c: c["hooks"].pop(),
            "duplicate-id": lambda c: c["hooks"].append(copy.deepcopy(c["hooks"][0])),
            "empty-prompt": lambda c: c["hooks"][0].update(prompt_template=" "),
            "unknown-variable": lambda c: c["hooks"][0].update(prompt_template="Use {{unknown_secret}}"),
            "unknown-domain": lambda c: c["hooks"][0].update(domain="author"),
            "unknown-cadence": lambda c: c["hooks"][0].update(cadence="every-minute"),
            "missing-calendar": lambda c: c["hooks"][2].update(requires=[]),
            "invalid-requires": lambda c: c["hooks"][0].update(requires="calendar"),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                self.hooks = copy.deepcopy(original)
                mutate(self.hooks)
                self.save()
                self.assertFalse(validator.validate(self.root)["ok"])

    def test_private_hook_data(self):
        self.hooks["hooks"][0]["prompt_template"] = "Read /home/example/private"
        self.save()
        self.assertFalse(validator.validate(self.root)["ok"])


if __name__ == "__main__":
    unittest.main()
