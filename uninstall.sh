#!/bin/bash
# Fallback uninstaller (in case you can't open the app's window).
# Reverts every applied icon and removes everything that was installed.
set -e

APP_DIR="$HOME/.local/share/cascabel-covers"
BASE_DIR="$HOME/.cascabel-covers"
DESKTOP_FILE="$HOME/.local/share/applications/cascabel-covers.desktop"
BIN_LINK="$HOME/.local/bin/cascabel-covers"
REGISTRY="$BASE_DIR/registry.json"

echo "== Uninstalling Cascabel Covers =="

if [ -f "$REGISTRY" ]; then
    echo "Reverting applied icons..."
    python3 - "$REGISTRY" <<'PYEOF'
import json, subprocess, sys, os
registry_path = sys.argv[1]
with open(registry_path) as f:
    registry = json.load(f)
for path in registry:
    if os.path.exists(path):
        subprocess.run(["gio", "set", "-t", "unset", path, "metadata::custom-icon"],
                        check=False, capture_output=True)
        print("Reverted:", os.path.basename(path))
PYEOF
    nemo -q >/dev/null 2>&1 || true
fi

rm -rf "$APP_DIR" "$BASE_DIR"
rm -f "$DESKTOP_FILE" "$BIN_LINK"

echo "Done, Cascabel Covers has been uninstalled."
