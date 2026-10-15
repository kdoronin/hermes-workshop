"""Keep documented state examples consistent with the actual checker/catalog."""
import importlib.util
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('checker', ROOT / 'scripts/check_setup_state.py')
assert spec is not None and spec.loader is not None
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class OnboardingContractTests(unittest.TestCase):
    def test_documented_state_is_complete_catalog_but_not_verified(self):
        text = (ROOT / 'ONBOARDING.md').read_text()
        examples = [json.loads(block) for block in re.findall(r'```json\n(.*?)\n```', text, re.S)]
        state = next(e for e in examples if 'schema_version' in e)
        catalog = json.loads((ROOT / 'modules.json').read_text())['modules']
        self.assertEqual({m['id'] for m in state['modules']}, {m['id'] for m in catalog})
        self.assertEqual(len(state['modules']), len(catalog))
        self.assertEqual({c['name'] for c in state['core_checks']}, checker.CORE_CHECKS)
        self.assertFalse(checker.validate_state(state, catalog)['ok'])
        # Synthetic fixture only: demonstrate that the published contract is satisfiable.
        for item in state['modules']:
            if item['choice'] in ('selected', 'existing'):
                item.update(status='verified', checks=[{
                    'name': 'synthetic test only', 'passed': True, 'evidence': 'synthetic reference'}])
        for check in state['core_checks']:
            check.update(passed=True, evidence='synthetic reference')
        self.assertTrue(checker.validate_state(state, catalog)['ok'])

    def test_entry_points_link_complete_route(self):
        for filename in ('README.md', 'INSTALLER.md'):
            text = (ROOT / filename).read_text()
            self.assertIn('(ONBOARDING.md)', text)
            self.assertIn('(TELEGRAM-SETUP.md)', text)
        text = (ROOT / 'ONBOARDING.md').read_text()
        self.assertIn('scripts/check_setup_state.py', text)
        telegram = (ROOT / 'TELEGRAM-SETUP.md').read_text()
        self.assertIn('/newbot', telegram)
        self.assertIn('TELEGRAM_ALLOWED_USERS', telegram)
        self.assertIn('telegram_after_modules', telegram)


if __name__ == '__main__':
    unittest.main()
