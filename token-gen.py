import json
import sys
import time
import requests
import jwt
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "config" / "environment.json"


def load_config():
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Config file not found: {CONFIG_PATH}")
    return json.loads(CONFIG_PATH.read_text())


def generate_jwt(config):
    key_path = Path(config["private_key_path"])
    if not key_path.is_absolute():
        key_path = Path(__file__).parent / key_path
    if not key_path.exists():
        raise FileNotFoundError(f"Private key not found: {key_path}")
    private_key = key_path.read_text()
    now = int(time.time())

    payload = {
        "iat": now - 60,
        "exp": now + 600,
        "iss": config["client_id"].strip()
    }

    return jwt.encode(payload, private_key, algorithm="RS256")


def get_latest_installation_id(jwt_token):
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Accept": "application/vnd.github+json"
    }
    response = requests.get("https://api.github.com/app/installations", headers=headers)
    response.raise_for_status()
    installations = response.json()

    if not installations:
        raise RuntimeError("No installations found for this GitHub App")

    latest = max(installations, key=lambda i: i["updated_at"])
    return latest["id"]


def get_installation_token(jwt_token, installation_id):
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Accept": "application/vnd.github+json"
    }
    url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
    response = requests.post(url, headers=headers)
    response.raise_for_status()
    return response.json()["token"]


try:
    config           = load_config()
    jwt_token        = generate_jwt(config)
    installation_id  = get_latest_installation_id(jwt_token)
    token            = get_installation_token(jwt_token, installation_id)
    print("username=x-access-token")
    print(f"password={token}")
except FileNotFoundError as e:
    print(f"error: {e}", file=sys.stderr)
    sys.exit(1)
except json.JSONDecodeError as e:
    print(f"error: failed to parse environment.json — {e}", file=sys.stderr)
    sys.exit(1)
except requests.HTTPError as e:
    print(f"error: GitHub API request failed — {e}", file=sys.stderr)
    sys.exit(1)
except requests.ConnectionError:
    print("error: could not reach GitHub API — check your network connection", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"error: {type(e).__name__}: {e}", file=sys.stderr)
    sys.exit(1)
