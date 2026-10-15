#!/usr/bin/env python3
"""Check a non-secret setup record offline. Does NOT verify a running Hermes.

Exit 0 means that the record is internally complete, not that its claims are true.
Only the installer observing real checks may populate the evidence references.
"""
import argparse
import json
from pathlib import Path
import re

CORE_CHECKS = frozenset({
    'runtime', 'model_reply', 'telegram_owner_access',
    'telegram_roundtrip', 'telegram_after_modules',
    'runtime_after_modules', 'model_reply_after_modules',
})
SECRET = re.compile(r'\b\d{6,}:[A-Za-z0-9_-]{25,}\b|\b(?:sk-[A-Za-z0-9_-]{16,})')
SECRET_KEYS = frozenset({'token', 'password', 'secret', 'api_key', 'bot_token',
                         'telegram_bot_token', 'authorization', 'env_contents'})


def contains_secret(value):
    """Best-effort guard, not a general secret scanner; never echo rejected input."""
    if isinstance(value, str):
        return bool(SECRET.search(value))
    if isinstance(value, dict):
        return any(str(k).lower() in SECRET_KEYS or contains_secret(v)
                   for k, v in value.items())
    if isinstance(value, list):
        return any(contains_secret(v) for v in value)
    return False


def valid_text(value):
    return isinstance(value, str) and bool(value.strip())


def check_observations(checks):
    """Require distinct named observations with exact booleans and references."""
    if not isinstance(checks, list) or not checks:
        return False
    names = set()
    for check in checks:
        if not isinstance(check, dict):
            return False
        name = check.get('name')
        if not valid_text(name) or name in names:
            return False
        names.add(name)
        if check.get('passed') is not True or not valid_text(check.get('evidence')):
            return False
    return True


def validate_state(state, catalog):
    """Validate explicit choices and recorded checks, without reading user config."""
    errors = []
    if not isinstance(state, dict):
        return {'ok': False, 'errors': ['state must be an object']}
    if contains_secret(state):
        return {'ok': False, 'errors': ['secret-like data found; remove secrets from record']}
    if type(state.get('schema_version')) is not int or state['schema_version'] != 1:
        errors.append('schema_version must be 1')
    target = state.get('target')
    if not isinstance(target, dict) or not all(valid_text(target.get(k)) for k in ('machine', 'profile')):
        errors.append('target machine and profile required')
    if state.get('selection_confirmed') is not True:
        errors.append('selection must be explicitly confirmed')
    core = state.get('core_checks')
    if not check_observations(core):
        errors.append('core observations must be unique, passed, and referenced')
    if not isinstance(core, list) or not CORE_CHECKS.issubset(
            {c.get('name') for c in core if isinstance(c, dict) and isinstance(c.get('name'), str)}):
        errors.append('runtime, model and all Telegram checks required')
    modules = state.get('modules')
    if not isinstance(modules, list):
        return {'ok': False, 'errors': errors + ['module choices required']}
    expected = {m['id']: m for m in catalog}
    actual = {}
    for item in modules:
        if not isinstance(item, dict) or not isinstance(item.get('id'), str):
            errors.append('malformed module record')
            continue
        mid = item['id']
        if mid not in expected or mid in actual:
            errors.append('unknown or duplicate module record')
            continue
        actual[mid] = item
        choice, status = item.get('choice'), item.get('status')
        if choice in ('selected', 'existing'):
            if status != 'verified' or not check_observations(item.get('checks')):
                errors.append(mid + ': selected module not verified')
        elif choice in ('skipped', 'later'):
            if status != 'not_applicable' or item.get('checks', []) != []:
                errors.append(mid + ': excluded module cannot claim installation')
        else:
            errors.append(mid + ': explicit choice required')
    if set(actual) != set(expected):
        errors.append('every catalog module must have exactly one choice')
    for mid, item in actual.items():
        if item.get('choice') not in ('selected', 'existing'):
            continue
        for dependency in expected[mid].get('requires', []):
            dep = actual.get(dependency, {})
            if dep.get('choice') not in ('selected', 'existing') or dep.get('status') != 'verified':
                errors.append(mid + ': dependency not explicitly selected and verified')
    return {'ok': not errors, 'errors': errors,
            'meaning': 'record consistency only; not live installation verification'}


def strict_json(text):
    """Reject duplicate keys and non-standard constants, without printing values."""
    def pairs(items):
        obj = {}
        for key, value in items:
            if key in obj:
                raise ValueError('duplicate JSON key')
            obj[key] = value
        return obj

    def constant(_value):
        raise ValueError('non-finite JSON constant')

    return json.loads(text, object_pairs_hook=pairs, parse_constant=constant)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('state', type=Path)
    args = parser.parse_args()
    try:
        state = strict_json(args.state.read_text(encoding='utf-8'))
        catalog_path = Path(__file__).resolve().parents[1] / 'modules.json'
        catalog = json.loads(catalog_path.read_text(encoding='utf-8'))['modules']
        result = validate_state(state, catalog)
    except (OSError, ValueError, KeyError, TypeError, RecursionError):
        result = {'ok': False, 'errors': ['cannot read valid state or module catalog']}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
