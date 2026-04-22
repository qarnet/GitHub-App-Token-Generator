"""Shared utilities for GitHub App authentication."""
import fcntl
import json
import os
import sys
import tempfile
import time

import requests
import jwt
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / 'config' / 'environment.json'
CACHE_DIR   = Path.home() / '.cache' / 'github-app-token-generator'
CACHE_FILE  = CACHE_DIR / 'token.json'


def load_config():
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f'Config file not found: {CONFIG_PATH}')
    data = json.loads(CONFIG_PATH.read_text())
    for key in ('client_id', 'private_key_path'):
        if not data.get(key):
            raise KeyError(f'Missing required config key: {key}')
    return data


def make_jwt(config):
    key_path = Path(config['private_key_path'])
    if not key_path.is_absolute():
        key_path = Path(__file__).parent / key_path
    if not key_path.exists():
        raise FileNotFoundError(f'Private key not found: {key_path}')
    private_key = key_path.read_text()
    now = int(time.time())
    return jwt.encode(
        {'iat': now - 60, 'exp': now + 600, 'iss': config['client_id'].strip()},
        private_key, algorithm='RS256')


def get_installations(jwt_token):
    resp = requests.get(
        'https://api.github.com/app/installations',
        headers={'Authorization': f'Bearer {jwt_token}', 'Accept': 'application/vnd.github+json'},
        timeout=10,
        verify=True)
    resp.raise_for_status()
    return resp.json()


def load_cache():
    try:
        return json.loads(CACHE_FILE.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def save_cache(data):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(CACHE_DIR, 0o700)
    data_bytes = json.dumps(data, indent=2).encode()
    fd, tmp_path = tempfile.mkstemp(dir=CACHE_DIR)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        os.write(fd, data_bytes)
        os.close(fd)
        os.chmod(tmp_path, 0o600)
        os.replace(tmp_path, CACHE_FILE)
    except Exception:
        try:
            os.unlink(tmp_path)
        except FileNotFoundError:
            pass
        raise
