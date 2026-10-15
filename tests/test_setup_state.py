"""Offline checks of completion records, never a live installation test."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'check_setup_state.py'
CATALOG = json.loads((ROOT / 'modules.json').read_text())['modules']


class SetupStateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.checker = None
        if SCRIPT.exists():
            spec = importlib.util.spec_from_file_location('setup_checker', SCRIPT)
            assert spec is not None and spec.loader is not None
            cls.checker = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cls.checker)

    def setUp(self):
        self.assertIsNotNone(self.checker, 'completion checker must exist')
        self.state = {
            'schema_version': 1,
            'target': {'machine': 'test-host', 'profile': 'test-profile'},
            'selection_confirmed': True,
            'modules': [{'id': m['id'], 'choice': 'skipped',
                         'status': 'not_applicable', 'checks': []} for m in CATALOG],
            'core_checks': [{'name': name, 'passed': True,
                             'evidence': 'private local record reference'} for name in (
                'runtime', 'model_reply', 'telegram_owner_access',
                'telegram_roundtrip', 'telegram_after_modules',
                'runtime_after_modules', 'model_reply_after_modules')],
        }

    def result(self):
        return self.checker.validate_state(self.state, CATALOG)

    def test_complete_without_optional_modules(self):
        before = copy.deepcopy(self.state)
        self.assertTrue(self.result()['ok'])
        self.assertEqual(self.state, before)

    def test_selected_module_needs_observation(self):
        item = self.state['modules'][0]
        item.update(choice='selected', status='verified')
        self.assertFalse(self.result()['ok'])
        item['checks'] = [{'name': 'behavior', 'passed': True, 'evidence': 'local test reference'}]
        self.assertTrue(self.result()['ok'])

    def test_pending_or_blocked_cannot_complete(self):
        for status in ('pending', 'blocked'):
            with self.subTest(status=status):
                self.state['modules'][0].update(choice='selected', status=status)
                self.assertFalse(self.result()['ok'])

    def test_missing_telegram_check(self):
        self.state['core_checks'].pop()
        self.assertFalse(self.result()['ok'])

    def test_failed_or_non_boolean_check(self):
        for value in (False, 'true', 1):
            self.state['core_checks'][0]['passed'] = value
            self.assertFalse(self.result()['ok'])

    def test_blank_observation_rejected(self):
        self.state['core_checks'][0]['evidence'] = '  '
        self.assertFalse(self.result()['ok'])

    def test_catalog_must_be_fully_accounted_for(self):
        self.state['modules'].pop()
        self.assertFalse(self.result()['ok'])

    def test_duplicate_and_unknown_modules(self):
        self.state['modules'].append(copy.deepcopy(self.state['modules'][0]))
        self.assertFalse(self.result()['ok'])
        self.state['modules'][-1]['id'] = 'unknown-module'
        self.assertFalse(self.result()['ok'])

    def test_unconfirmed_choice_or_target(self):
        self.state['selection_confirmed'] = False
        self.assertFalse(self.result()['ok'])
        self.state['selection_confirmed'] = True
        self.state['target']['profile'] = ''
        self.assertFalse(self.result()['ok'])

    def test_dependency_must_be_explicitly_selected_and_verified(self):
        item = next(m for m in self.state['modules'] if m['id'] == 'book-library-setup')
        item.update(choice='selected', status='verified', checks=[{
            'name': 'behavior', 'passed': True, 'evidence': 'local test reference'}])
        self.assertFalse(self.result()['ok'])
        dep = next(m for m in self.state['modules'] if m['id'] == 'llm-wiki-hermes-setup')
        dep.update(choice='existing', status='verified', checks=copy.deepcopy(item['checks']))
        self.assertTrue(self.result()['ok'])

    def test_skipped_or_later_not_claimed_as_installed(self):
        for choice in ('skipped', 'later'):
            self.state['modules'][0].update(choice=choice, status='verified')
            self.assertFalse(self.result()['ok'])

    def test_secret_is_rejected_without_echo(self):
        secret = '123456789:' + 'A' * 35
        self.state['core_checks'][0]['evidence'] = secret
        result = self.result()
        self.assertFalse(result['ok'])
        self.assertNotIn(secret, json.dumps(result))

    def test_malformed_state_fails_closed(self):
        for state in (None, [], {}, {'schema_version': 1, 'modules': None}):
            with self.subTest(state=state):
                self.assertFalse(self.checker.validate_state(state, CATALOG)['ok'])

    def test_duplicate_check_names_rejected(self):
        self.state['core_checks'].append(copy.deepcopy(self.state['core_checks'][0]))
        self.assertFalse(self.result()['ok'])

    def test_post_module_runtime_and_model_checks_required(self):
        for name in ('runtime_after_modules', 'model_reply_after_modules'):
            state = copy.deepcopy(self.state)
            state['core_checks'] = [c for c in state['core_checks'] if c['name'] != name]
            self.assertFalse(self.checker.validate_state(state, CATALOG)['ok'])

    def test_cli_rejects_ambiguous_and_deep_json(self):
        import os
        import tempfile
        # Include all required checks so rejection is due to parsing, not omission.
        state = copy.deepcopy(self.state)
        for name in ('runtime_after_modules', 'model_reply_after_modules'):
            if not any(c['name'] == name for c in state['core_checks']):
                state['core_checks'].append({'name': name, 'passed': True, 'evidence': 'local record'})
        text = json.dumps(state)
        cases = [
            text.replace('"selection_confirmed": true', '"selection_confirmed": false, "selection_confirmed": true'),
            text[:-1] + ', "extra": NaN}',
            text[:-1] + ', "extra": ' + '[' * 600 + '0' + ']' * 600 + '}',
        ]
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as folder:
            path = Path(folder) / 'record.json'
            for text in cases:
                with self.subTest(case=text[:40]):
                    path.write_text(text)
                    result = subprocess.run([sys.executable, str(SCRIPT), str(path)],
                                            capture_output=True, text=True)
                    self.assertEqual(result.returncode, 1)
                    self.assertFalse(json.loads(result.stdout)['ok'])
                    self.assertNotIn('Traceback', result.stderr)

    def test_cli_bad_input_is_nonzero(self):
        result = subprocess.run([sys.executable, str(SCRIPT), str(ROOT / 'modules.json')],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(json.loads(result.stdout)['ok'])


if __name__ == '__main__':
    unittest.main()
