"""Interactive GitHub App installation discovery — called by install.sh.

Lists all installations for the configured GitHub App. If there is only
one, selects it automatically. If there are multiple, prompts the user
to choose. Writes the selected installation_id to the token cache so
token-gen.py can use it on every subsequent run without hitting the API.
"""
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


def write_installation_id(installation_id):
    try:
        cache = load_cache()
    except (OSError, json.JSONDecodeError):
        cache = {}
    cache['installation_id'] = installation_id
    save_cache(cache)


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
except OSError as e:
    print(f'error: OS error — {e}', file=sys.stderr)
    sys.exit(1)
