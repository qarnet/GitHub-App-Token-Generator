# Further Improvements

Issues identified during code review. No changes made yet — tracked here for future work.

---

## 1. `fcntl.flock` in `save_cache` is ineffective
**File:** `github_app_auth.py` — `save_cache()`

`tempfile.mkstemp()` gives each process a unique file descriptor, so `fcntl.flock(fd, LOCK_EX)` never contends between processes — the lock is effectively a no-op for mutual exclusion. The write is safe in practice because `os.replace()` is atomic on Linux (POSIX), but the flock gives a false impression of protection.

**Fix options:**
- Remove the flock entirely (atomic replace is sufficient for this use case).
- Replace it with a dedicated lockfile (e.g. `CACHE_DIR / 'token.lock'`) for true inter-process mutual exclusion.

---

## 2. Unused `import sys` in `github_app_auth.py`
**File:** `github_app_auth.py`, line 5

`sys` is imported but never referenced anywhere in the module. Dead import.

**Fix:** Remove the line.

---

## 3. Unpinned dependencies in `requirements.txt`
**File:** `requirements.txt`

All three dependencies (`requests`, `PyJWT`, `cryptography`) are unpinned. The `cryptography` package in particular has had breaking API changes across major versions. A fresh install on a new machine could pull in an incompatible version in the future.

**Fix:** Pin to minimum known-good versions, e.g.:
```
requests>=2.32
PyJWT>=2.8
cryptography>=42.0
```

---

## 4. `token-gen.py` executes at import time
**File:** `token-gen.py`

The entire execution block (try/except with `sys.exit()` calls) runs at module level with no `if __name__ == '__main__':` guard. Importing the module triggers side effects immediately, which makes unit testing impossible without subprocess isolation.

**Fix:** Wrap the execution block:
```python
if __name__ == '__main__':
    # ... existing try/except block ...
```

---

## 5. `os.chmod(CACHE_DIR, 0o700)` called on every token save
**File:** `github_app_auth.py` — `save_cache()`

`chmod` is called on the cache directory on every save (approximately once per hour), even when the permissions are already correct. Minor unnecessary syscall.

**Fix:** Condition the chmod on whether the directory was newly created, using `mkdir` return value or checking before creating.
