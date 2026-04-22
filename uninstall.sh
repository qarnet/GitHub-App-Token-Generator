#!/usr/bin/env bash
set -euo pipefail

# ── Colours ────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
RESET='\033[0m'

info()    { echo -e "${BOLD}$*${RESET}"; }
success() { echo -e "${GREEN}\u2714 $*${RESET}"; }
warn()    { echo -e "${YELLOW}\u26a0 $*${RESET}"; }
error()   { echo -e "${RED}\u2718 $*${RESET}" >&2; }

# ── Directory check ───────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HELPER="$SCRIPT_DIR/get-token.sh"

# ── Remove git credential helper ──────────────────────────────────────────
info "--- Removing git credential helper ---"
if git config --global "credential.https://github.com.helper" &>/dev/null; then
    CURRENT_HELPER=$(git config --global "credential.https://github.com.helper")
    if [[ "$CURRENT_HELPER" == "$HELPER" ]]; then
        git config --global --unset "credential.https://github.com.helper"
        success "Removed credential helper from ~/.gitconfig"
    else
        warn "credential.https://github.com.helper points to a different helper:"
        warn "  $CURRENT_HELPER"
        warn "Not modifying it."
    fi
else
    warn "No credential helper registered for https://github.com"
fi

# ── Remove cache ────────────────────────────────────────────────────────
info "--- Removing token cache ---"
CACHE_DIR="$HOME/.cache/github-app-token-generator"
if [[ -d "$CACHE_DIR" ]]; then
    rm -rf "$CACHE_DIR"
    success "Removed $CACHE_DIR"
else
    warn "Cache directory not found: $CACHE_DIR"
fi

# ── Optional: remove config ─────────────────────────────────────────────
info "--- Removing config ---"
CONFIG_DIR="$SCRIPT_DIR/config"
if [[ -d "$CONFIG_DIR" ]]; then
    read -rp "Remove config/ directory (contains private key and environment.json)? [y/N] " confirm
    if [[ "$confirm" =~ ^[Yy]$ ]]; then
        rm -rf "$CONFIG_DIR"
        success "Removed config/"
    else
        warn "Kept config/ directory"
    fi
else
    warn "config/ directory not found"
fi

success "Uninstall complete."
