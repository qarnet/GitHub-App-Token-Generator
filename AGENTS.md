# Agent Notes — github-app-token-generator

## Repo Overview
Small Python/bash tooling repo: a git credential helper that authenticates to GitHub as an App using short-lived installation tokens.

## Entry Points
- **`get-token.sh`** — The shell git actually invokes as the credential helper. It simply calls `token-gen.py`.
- **`token-gen.py`** — Fetches (and caches) an installation token, then prints `username=x-access-token\npassword=<token>`.
- **`discover-installation.py`** — Interactive installation selector; only called by `install.sh`.
- **`install.sh`** — Interactive setup wizard. Requires human input; do not run unattended.

## Architecture
- **`github_app_auth.py`** — Shared module with `load_config()`, `make_jwt()`, `get_installations()`, `load_cache()`, `save_cache()`, and constants. Both `token-gen.py` and `discover-installation.py` import from it.
- `config/environment.json` holds `client_id`, `private_key_path`, and optionally `installation_id`.
- Private key PEM lives inside `config/` (not committed; `config/` is gitignored).
- Token cache lives at `~/.cache/github-app-token-generator/token.json`.

## Dependencies
Runtime deps are listed in `requirements.txt` (also checked by `install.sh`):
- `requests`
- `PyJWT`
- `cryptography`

Install: `pip3 install -r requirements.txt`

## Safe Defaults
- All API requests go to `https://api.github.com` (no Enterprise support yet).
- `verify=True` is implicit on `requests` calls.
- Cache directory created with `0o700`, cache file with `0o600`.

## Conventions
- `client_id` must begin with `Iv1.` (unenforced at runtime but expected).
- `private_key_path` in `environment.json` can be relative (resolved from repo root) or absolute.
- Errors are printed to `stderr` so git surfaces them.

## Workspace Notes
- `.opencode/SECURITY-AND-QOL-PLAN.md` contains the canonical security/QoL roadmap. Review it before substantial changes.
- `.opencode/` and `config/` are gitignored.
