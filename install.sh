#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HELPER="$SCRIPT_DIR/get-token.sh"

git config --global "credential.https://github.com.helper" "$HELPER"

echo "Credential helper registered for https://github.com"
echo "  Helper: $HELPER"
echo ""
echo "To verify:"
echo "  git config --global credential.https://github.com.helper"
