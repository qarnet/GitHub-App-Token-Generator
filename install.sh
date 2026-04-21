#!/bin/bash
set -euo pipefail

# ── Colours ────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
RESET='\033[0m'

info()    { echo -e "${BOLD}$*${RESET}"; }
success() { echo -e "${GREEN}✔ $*${RESET}"; }
warn()    { echo -e "${YELLOW}⚠ $*${RESET}"; }
error()   { echo -e "${RED}✘ $*${RESET}" >&2; }

# ── Step 1 — Intro + directory check ──────────────────────────────────────
echo ""
info "=== GitHub App Credential Helper — Setup ==="
echo ""
echo "This script will:"
echo "  1. Create a config/ folder in the current directory"
echo "  2. Ask for your GitHub App Client ID"
echo "  3. Ask for your private key filename (must already be in config/)"
echo "  4. Write config/environment.json"
echo "  5. Apply secure file permissions to config/"
echo "  6. Register the credential helper in ~/.gitconfig (scoped to github.com)"
echo "  7. Run a smoke test to verify everything works"
echo ""

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [[ ! -f "$SCRIPT_DIR/token-gen.py" || ! -f "$SCRIPT_DIR/get-token.sh" ]]; then
    error "This script must be run from inside the agent-environment repository."
    error "Expected to find token-gen.py and get-token.sh in: $SCRIPT_DIR"
    exit 1
fi

if [[ "$(pwd)" != "$SCRIPT_DIR" ]]; then
    warn "You are not running this script from its own directory."
    warn "Current directory : $(pwd)"
    warn "Script directory  : $SCRIPT_DIR"
    echo ""
    read -rp "Continue anyway? [y/N] " confirm
    [[ "$confirm" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 0; }
    echo ""
fi

success "Running from correct directory: $SCRIPT_DIR"
echo ""

# ── Step 2 — Create config/ ────────────────────────────────────────────────
CONFIG_DIR="$SCRIPT_DIR/config"

if [[ -d "$CONFIG_DIR" ]]; then
    warn "config/ already exists — skipping creation."
else
    mkdir "$CONFIG_DIR"
    success "Created config/"
fi
echo ""

# ── Read existing environment.json if present ─────────────────────────────
ENV_FILE="$CONFIG_DIR/environment.json"
EXISTING_CLIENT_ID=""
EXISTING_KEY_NAME=""

if [[ -f "$ENV_FILE" ]]; then
    warn "config/environment.json already exists — checking existing values."
    echo ""
    EXISTING_CLIENT_ID=$(python3 -c "import json; d=json.load(open('$ENV_FILE')); print(d.get('client_id',''))" 2>/dev/null || echo "")
    EXISTING_KEY_PATH=$(python3 -c "import json; d=json.load(open('$ENV_FILE')); print(d.get('private_key_path',''))" 2>/dev/null || echo "")
    EXISTING_KEY_NAME=$(basename "$EXISTING_KEY_PATH")
fi

# ── Step 3 — Client ID ─────────────────────────────────────────────────────
info "--- GitHub App Client ID ---"
echo "Found on your GitHub App's settings page under 'Client ID'."
echo ""
if [[ -n "$EXISTING_CLIENT_ID" ]]; then
    echo "Current value: ${BOLD}$EXISTING_CLIENT_ID${RESET}"
    read -rp "Is this still correct? [Y/n] " confirm
    if [[ "$confirm" =~ ^[Nn]$ ]]; then
        EXISTING_CLIENT_ID=""
    fi
fi
if [[ -z "$EXISTING_CLIENT_ID" ]]; then
    while true; do
        read -rp "Client ID: " CLIENT_ID
        CLIENT_ID="${CLIENT_ID// /}"
        [[ -n "$CLIENT_ID" ]] && break
        error "Client ID cannot be empty. Please try again."
    done
else
    CLIENT_ID="$EXISTING_CLIENT_ID"
    success "Keeping existing Client ID: $CLIENT_ID"
fi
echo ""

# ── Step 4 — Private key filename ─────────────────────────────────────────
info "--- Private Key ---"
echo "The private key file must already be placed inside config/"
echo "before continuing. Download it from your GitHub App settings page."
echo "Example filename: private-key.pem"
echo ""
if [[ -n "$EXISTING_KEY_NAME" ]]; then
    echo "Current value: ${BOLD}$EXISTING_KEY_NAME${RESET}"
    read -rp "Is this still correct? [Y/n] " confirm
    if [[ "$confirm" =~ ^[Nn]$ ]]; then
        EXISTING_KEY_NAME=""
    fi
fi
if [[ -z "$EXISTING_KEY_NAME" ]]; then
    while true; do
        read -rp "Private key filename (inside config/): " KEY_NAME
        KEY_NAME="${KEY_NAME// /}"
        if [[ -z "$KEY_NAME" ]]; then
            error "Filename cannot be empty. Please try again."
            continue
        fi
        KEY_PATH="$CONFIG_DIR/$KEY_NAME"
        if [[ ! -f "$KEY_PATH" ]]; then
            error "File not found: $KEY_PATH"
            error "Copy your private key into config/ and then re-enter the filename."
            continue
        fi
        break
    done
else
    KEY_NAME="$EXISTING_KEY_NAME"
    KEY_PATH="$CONFIG_DIR/$KEY_NAME"
    if [[ ! -f "$KEY_PATH" ]]; then
        error "Expected key file not found: $KEY_PATH"
        error "Copy your private key into config/ and re-run."
        exit 1
    fi
    success "Keeping existing private key: $KEY_NAME"
fi
echo ""

# ── Step 5 — Write environment.json ───────────────────────────────────────
cat > "$ENV_FILE" <<EOF
{
  "client_id": "$CLIENT_ID",
  "private_key_path": "config/$KEY_NAME"
}
EOF

info "--- Review environment.json ---"
echo ""
cat "$ENV_FILE"
echo ""
read -rp "Does this look correct? Continue? [y/N] " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "Aborted. Edit config/environment.json manually and re-run if needed."
    exit 0
fi
echo ""

# ── Step 6 — Permissions ───────────────────────────────────────────────────
info "--- Applying permissions ---"
chmod 700 "$CONFIG_DIR"
success "chmod 700 config/"
chmod 600 "$KEY_PATH"
success "chmod 600 config/$KEY_NAME"
chmod 600 "$ENV_FILE"
success "chmod 600 config/environment.json"
echo ""

# ── Step 7 — Register credential helper ───────────────────────────────────
info "--- Registering git credential helper ---"
HELPER="$SCRIPT_DIR/get-token.sh"
chmod +x "$HELPER"
success "chmod +x get-token.sh"
git config --global "credential.https://github.com.helper" "$HELPER"
success "Registered: credential.https://github.com.helper = $HELPER"
echo ""

# ── Step 8 — Smoke test ────────────────────────────────────────────────────
info "--- Smoke test ---"
echo "Running token-gen.py to verify the full authentication flow..."
echo ""
if python3 "$SCRIPT_DIR/token-gen.py" | grep -q "^username=x-access-token"; then
    success "Token generated successfully — credential helper is working."
else
    error "token-gen.py ran but did not produce expected output."
    error "Check your Client ID and private key, then re-run."
    exit 1
fi

echo ""
success "Setup complete."
echo ""
echo "From now on, every 'git push' or 'git pull' to github.com will"
echo "automatically use a fresh short-lived token from your GitHub App."
echo ""
