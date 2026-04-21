# Security & Quality of Life Improvement Plan

## Phase 1: Critical Security Fixes

### 1.1 — Atomic cache file writes (TOCTOU fix)
**Files:** `token-gen.py`, `discover-installation.py`

`write_text()` creates files with default permissions before `chmod` restricts them. A local attacker can read the token in that window.

**Fix:** Write to a temp file with restrictive permissions, then atomic rename:
```python
import tempfile, os

def save_cache(data):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(CACHE_DIR, 0o700)
    data_bytes = json.dumps(data, indent=2).encode()
    fd, tmp_path = tempfile.mkstemp(dir=CACHE_DIR)
    try:
        os.write(fd, data_bytes)
        os.close(fd)
        os.chmod(tmp_path, 0o600)
        os.replace(tmp_path, CACHE_FILE)
    except:
        os.unlink(tmp_path)
        raise
```

### 1.2 — Safe JSON generation in `install.sh`
**File:** `install.sh:174-179`

Unquoted heredoc shell-expands `$CLIENT_ID`/`$KEY_NAME`, allowing injection.

**Fix:** Use Python for safe JSON:
```bash
python3 -c "
import json, sys
json.dump({
    'client_id': sys.argv[1],
    'private_key_path': f'config/{sys.argv[2]}',
}, open(sys.argv[3], 'w'), indent=2)
" "$CLIENT_ID" "$KEY_NAME" "$ENV_FILE"
```

### 1.3 — Eliminate shell-interpolated `python3 -c`
**File:** `install.sh:103-104`

**Fix:** Pass filename as argv instead of interpolating into string:
```bash
EXISTING_CLIENT_ID=$(python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(d.get('client_id',''))" "$ENV_FILE" 2>/dev/null || echo "")
```

---

## Phase 2: Medium Security Fixes

| # | Fix | File(s) |
|---|-----|---------|
| 2.1 | Validate Client ID matches `Iv1.` prefix | `install.sh` |
| 2.2 | Validate required config keys (`client_id`, `private_key_path`) in `load_config()` | `token-gen.py`, `discover-installation.py` |
| 2.3 | Add `fcntl.flock` file locking on cache to prevent concurrent write corruption | `token-gen.py` |
| 2.4 | Explicitly set `verify=True` on all `requests` calls | `token-gen.py`, `discover-installation.py` |
| 2.5 | Replace broad `except Exception` with specific exceptions; sanitize error messages | `token-gen.py` |

---

## Phase 3: Code Deduplication

### 3.1 — Extract shared module
Create `github_app_auth.py` with shared logic:
- `load_config()`, `make_jwt()`, `get_installations()`
- `save_cache()`, `load_cache()`
- Constants: `CONFIG_PATH`, `CACHE_DIR`, `CACHE_FILE`

Both `token-gen.py` and `discover-installation.py` import from it.

---

## Phase 4: Quality of Life

| # | Fix | Detail |
|---|-----|--------|
| 4.1 | Add `requirements.txt` | `requests`, `PyJWT`, `cryptography` |
| 4.2 | Add `uninstall.sh` | Undo git config, remove cache, optionally remove config |
| 4.3 | Configurable API base URL | Support GitHub Enterprise via `api_base_url` in config |
| 4.4 | Non-interactive install mode | `--non-interactive` flag with env var overrides |
| 4.5 | venv guidance in README | Replace bare `pip3 install` with venv instructions |
| 4.6 | CLI argument parsing | Add `--verbose`/`--debug` flags |

---

## Execution Priority

| Order | Item | Impact |
|-------|------|--------|
| 1 | 1.1 Atomic cache writes | Critical security |
| 2 | 1.2 Safe JSON generation | Critical security |
| 3 | 1.3 Fix shell interpolation | High security |
| 4 | 2.1–2.5 Medium security fixes | Defense in depth |
| 5 | 3.1 Code deduplication | Maintainability |
| 6 | 4.1 `requirements.txt` | Quick win |
| 7 | 4.2–4.6 QoL improvements | Usability |