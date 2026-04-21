"""
Interactive GitHub App installation discovery — called by install.sh.

Lists all installations for the configured GitHub App. If there is only
one, selects it automatically. If there are multiple, prompts the user
to choose. Writes the selected installation_id to the token cache so
token-gen.py can use it on every subsequent run without hitting the API.
"""
import json
import os
import sys
import time
import requests
import jwt
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / 'config' / 'environment.json'
CACHE_DIR   = Path.home() / '.cache' / 'agent-environment'
CACHE_FILE  = CACHE_DIR / 'token.json'


def load_config():
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f'Config not found: {CONFIG_PATH}')
    return json.loads(CONFIG_PATH.read_text())


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
        timeout=10)
    resp.raise_for_status()
    return resp.json()


def write_installation_id(installation_id):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(CACHE_DIR, 0o700)
    try:
        cache = json.loads(CACHE_FILE.read_text())
    except Exception:
        cache = {}
    cache['installation_id'] = installation_id
    CACHE_FILE.write_text(json.dumps(cache, indent=2))
    os.chmod(CACHE_FILE, 0o600)


def fmt_installation(inst):
    acct = inst.get('account', {})
    return f'{acct.get("login", "?")} ({acct.get("type", "?")})'


try:
    config        = load_config()
    jwt_token     = make_jwt(config)
    installations = get_installations(jwt_token)

    if not installations:
        print('error: no installations found for this GitHub App.', file=sys.stderr)
        sys.exit(1)

    if len(installations) == 1:
        inst = installations[0]
        print(f'One installation found: {fmt_installation(inst)}')
        write_installation_id(inst['id'])
        print(f'Installation ID {inst["id"]} cached.')
        sys.exit(0)

    # Multiple installations — prompt the user
    print(f'Found {len(installations)} installations for this GitHub App. Select one:\n')
    for i, inst in enumerate(installations, 1):
        print(f'  {i}. {fmt_installation(inst)} — ID {inst["id"]}')
    print()

    while True:
        try:
            choice = input(f'Enter number [1-{len(installations)}]: ').strip()
            idx = int(choice) - 1
            if 0 <= idx < len(installations):
                break
        except (ValueError, EOFError):
            pass
        print(f'Please enter a number between 1 and {len(installations)}.')

    selected = installations[idx]
    write_installation_id(selected['id'])
    print(f'\nSelected: {fmt_installation(selected)} — Installation ID {selected["id"]} cached.')

except FileNotFoundError as e:
    print(f'error: {e}', file=sys.stderr)
    sys.exit(1)
except requests.HTTPError as e:
    print(f'error: GitHub API request failed — {e}', file=sys.stderr)
    sys.exit(1)
except requests.ConnectionError:
    print('error: could not reach GitHub API — check your network connection', file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f'error: {type(e).__name__}: {e}', file=sys.stderr)
    sys.exit(1)
