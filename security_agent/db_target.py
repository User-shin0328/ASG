"""Public target identity shared by enforcement and execution, without credentials."""
import os
import re


def target_config(environ=None):
    env = os.environ if environ is None else environ
    backend = env.get('PROTECTED_DB_BACKEND', 'sqlite')
    if backend not in {'sqlite', 'postgresql'}:
        raise ValueError('Unsupported protected DB backend')
    target = env.get('PROTECTED_DB_TARGET_ID', 'sqlite-lab-v1' if backend == 'sqlite' else '')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,79}', target):
        raise ValueError('A protected DB target ID is required')
    return {'backend': backend, 'id': target}
