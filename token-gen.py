import json
import os
import sys
import time
import requests
import jwt
from datetime import datetime, timezone
from pathlib import Path

CONFIG_PATH   = Path(__file__).parent / 'config' / 'environment.json'
CACHE_DIR     = Path.home() / '.cache' / 'agent-environment'
CACHE_FILE    = CACHE_DIR / 'token.json'
EXPIRY_BUFFER = 300  # seconds — refresh token 5 minutes before it expires


def load_config():
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f'Config file not found: {CONFIG_PATH}')
    return json.loads(CONFIG_PATH.read_text())


def load_cache():
    try:
        return json.loads(CACHE_FILE.read_text())
    except Exception:
        return {}


def save_cache(data):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(CACHE_DIR, 0o700)
    CACHE_FILE.write_text(json.dumps(data, indent=2))
    os.chmod(CACHE_FILE, 0o600)


def token_valid(cache):
    token      = cache.get('token')
    expires_at = cache.get('expires_at')
    if not token or not expires_at:
        return False
    expiry    = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
    remaining = (expiry - datetime.now(timezone.utc)).total_seconds()
    return remaining > EXPIRY_BUFFER


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


def resolve_installation_id(config, cache, jwt_token):
    # 1. Pinned explicitly in environment.json — always takes precedence
    if 'installation_id' in config:
        return config['installation_id']

    # 2. Previously cached (selected during install.sh or auto-discovered)
    if 'installation_id' in cache:
        return cache['installation_id']

    # 3. Discover from API
    installations = get_installations(jwt_token)

    if not installations:
        raise RuntimeError('No installations found for this GitHub App.')

    if len(installations) == 1:
        return installations[0]['id']

    # Multiple installations — cannot prompt non-interactively
    lines = [
        'Multiple GitHub App installations found. Cannot select automatically.',
        'Run ./install.sh to select one, or add "installation_id" to config/environment.json.',
        '',
        'Available installations:',
    ]
    for inst in installations:
        acct = inst.get('account', {})
        lines.append(f'  {inst["id"]} — {acct.get("login", "?")} ({acct.get("type", "?")})')
    raise RuntimeError('\n'.join(lines))


def fetch_token(jwt_token, installation_id):
    resp = requests.post(
        f'https://api.github.com/app/installations/{installation_id}/access_tokens',
        headers={'Authorization': f'Bearer {jwt_token}', 'Accept': 'application/vnd.github+json'},
        timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return data['token'], data['expires_at']


try:
    config = load_config()
    cache  = load_cache()

    # Use cached token if it's still valid
    if token_valid(cache):
        print('username=x-access-token')
        print(f'password={cache["token"]}')
        sys.exit(0)

    jwt_token       = make_jwt(config)
    installation_id = resolve_installation_id(config, cache, jwt_token)
    token, expires_at = fetch_token(jwt_token, installation_id)

    save_cache({
        'token':           token,
        'expires_at':      expires_at,
        'installation_id': installation_id,
    })

    print('username=x-access-token')
    print(f'password={token}')

except FileNotFoundError as e:
    print(f'error: {e}', file=sys.stderr)
    sys.exit(1)
except json.JSONDecodeError as e:
    print(f'error: failed to parse environment.json — {e}', file=sys.stderr)
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
