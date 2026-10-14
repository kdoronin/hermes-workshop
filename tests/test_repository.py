"""Offline regression checks for package validation; no live installation."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_repository.py"
spec = importlib.util.spec_from_file_location("workshop_validator", SCRIPT)
assert spec is not None and spec.loader is not None
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        self.root = Path(self.tmp.name)
        self.catalog = {
            "schema_version": 1,
            "installation_policy": "explicit-selection-only",
            "modules": [{"id": "demo", "file": "demo.md", "requires": [],
                         "default_selected": False, "risk": "normal",
                         "recommended_for_start": False}],
        }
        (self.root / "README.md").write_text("[Demo](demo.md)\n", encoding="utf-8")
        (self.root / "demo.md").write_text("# Demo\n", encoding="utf-8")
        self.save_catalog()

    def tearDown(self):
        self.tmp.cleanup()

    def save_catalog(self):
        (self.root / "modules.json").write_text(json.dumps(self.catalog), encoding="utf-8")

    def test_valid_package(self):
        self.assertTrue(validator.validate(self.root)["ok"])

    def test_missing_module(self):
        (self.root / "demo.md").unlink()
        self.assertFalse(validator.validate(self.root)["ok"])

    def test_default_selection_rejected(self):
        self.catalog["modules"][0]["default_selected"] = True
        self.save_catalog()
        self.assertFalse(validator.validate(self.root)["ok"])

    def test_high_risk_not_recommended(self):
        self.catalog["modules"][0].update(risk="high", recommended_for_start=True)
        self.save_catalog()
        self.assertFalse(validator.validate(self.root)["ok"])

    def test_dependency_cycle(self):
        self.catalog["modules"][0]["requires"] = ["demo"]
        self.save_catalog()
        self.assertFalse(validator.validate(self.root)["ok"])

    def test_unknown_dependency(self):
        self.catalog["modules"][0]["requires"] = ["absent"]
        self.save_catalog()
        self.assertFalse(validator.validate(self.root)["ok"])

    def test_personal_path(self):
        (self.root / "demo.md").write_text("Path: /Users/example/private\n", encoding="utf-8")
        self.assertFalse(validator.validate(self.root)["ok"])

    def test_unclosed_fence(self):
        (self.root / "demo.md").write_text("```text\nunclosed\n", encoding="utf-8")
        self.assertFalse(validator.validate(self.root)["ok"])

    def test_nested_fence(self):
        text = "````markdown\n---\nname: demo\ndescription: Demo skill.\n---\n# Demo\n```python\nx = 1\n```\n````\n"
        blocks, unclosed = validator.fenced_blocks(text)
        self.assertIsNone(unclosed)
        self.assertEqual(len(blocks), 1)
        (self.root / "demo.md").write_text(text, encoding="utf-8")
        self.assertTrue(validator.validate(self.root)["ok"])

    def test_yaml_metadata_not_skill(self):
        text = "```yaml\n---\ntitle: Example\ntype: book\n---\n```\n"
        (self.root / "demo.md").write_text(text, encoding="utf-8")
        self.assertTrue(validator.validate(self.root)["ok"])

    def test_python_syntax(self):
        (self.root / "demo.md").write_text("```python\nif:\n```\n", encoding="utf-8")
        self.assertFalse(validator.validate(self.root)["ok"])

    def test_duplicate_module(self):
        self.catalog["modules"].append(copy.deepcopy(self.catalog["modules"][0]))
        self.save_catalog()
        self.assertFalse(validator.validate(self.root)["ok"])

    def test_no_mutation(self):
        before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        validator.validate(self.root)
        after = {p.name: p.read_bytes() for p in self.root.iterdir()}
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
