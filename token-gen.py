"""Fetches (and caches) an installation token, then prints git credentials."""
import json
import os
import sys

import jwt
import requests

from github_app_auth import (
    load_config,
    load_cache,
    save_cache,
    make_jwt,
    get_installations,
)
from datetime import datetime, timezone

EXPIRY_BUFFER = 300  # seconds — refresh token 5 minutes before it expires


def token_valid(cache):
    token      = cache.get('token')
    expires_at = cache.get('expires_at')
    if not token or not expires_at:
        return False
    expiry    = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
    remaining = (expiry - datetime.now(timezone.utc)).total_seconds()
    return remaining > EXPIRY_BUFFER


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
        timeout=10,
        verify=True)
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
except KeyError as e:
    print(f'error: missing required config key — {e}', file=sys.stderr)
    sys.exit(1)
except jwt.PyJWTError as e:
    print(f'error: JWT signing failed — {e}', file=sys.stderr)
    sys.exit(1)
except requests.HTTPError as e:
    print(f'error: GitHub API request failed — {e}', file=sys.stderr)
    sys.exit(1)
except requests.ConnectionError:
    print('error: could not reach GitHub API — check your network connection', file=sys.stderr)
    sys.exit(1)
except RuntimeError as e:
    print(f'error: {e}', file=sys.stderr)
    sys.exit(1)
except OSError as e:
    print(f'error: OS error — {e}', file=sys.stderr)
    sys.exit(1)
