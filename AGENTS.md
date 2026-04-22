# Agent Notes — github-app-token-generator

## Repo Overview
Small Python/bash tooling repo: a git credential helper that authenticates to GitHub as an App using short-lived installation tokens.

## Entry Points
- **`get-token.sh`** — The shell git actually invokes as the credential helper. It simply calls `token-gen.py`.
- **`token-gen.py`** — Fetches (and caches) an installation token, then prints `username=x-access-token\npassword=<token>`.
- **`discover-installation.py`** — Interactive installation selector; only called by `install.sh`.
- **`install.sh`** — Interactive setup wizard. Requires human input; do not run unattended.

## Architecture
- Two Python scripts (`token-gen.py`, `discover-installation.py`) duplicate JWT and config logic.
- `config/environment.json` holds `client_id` and `private_key_path`.
- Private key PEM lives inside `config/` (not committed; `config/` is gitignored).
- Token cache lives at `~/.cache/github-app-token-generator/token.json`.

## Dependencies
No `requirements.txt` or packaging yet. Runtime deps (checked by `install.sh`):
- `requests`
- `PyJWT`
- `cryptography`

Install manually: `pip3 install requests PyJWT cryptography`

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
