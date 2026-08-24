#!/bin/bash
# Cascabel Covers installer for Linux Mint Cinnamon (Nemo)
set -e

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$HOME/.local/share/cascabel-covers"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"

echo "== Installing Cascabel Covers =="

# 1) Dependencies: PyGObject (usually already installed on Cinnamon)
if ! python3 -c "import gi; gi.require_version('Gtk','3.0'); from gi.repository import Gtk" 2>/dev/null; then
    echo "Missing PyGObject/GTK for Python. Installing..."
    sudo apt update
    sudo apt install -y python3-gi gir1.2-gtk-3.0
fi

if ! command -v gio >/dev/null 2>&1; then
    echo "Missing 'gio' (libglib2.0-bin). Installing..."
    sudo apt install -y libglib2.0-bin
fi

# 2) Copy the app
mkdir -p "$APP_DIR" "$BIN_DIR" "$DESKTOP_DIR"
cp "$SRC_DIR/cascabel-covers.py" "$APP_DIR/cascabel-covers.py"
chmod +x "$APP_DIR/cascabel-covers.py"

# 3) Terminal command
ln -sf "$APP_DIR/cascabel-covers.py" "$BIN_DIR/cascabel-covers"

# 4) Application menu entry
cat > "$DESKTOP_DIR/cascabel-covers.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Cascabel Covers
Comment=Apply box art as the icon for your NES, SNES and N64 ROMs
Exec=$APP_DIR/cascabel-covers.py
Icon=applications-games
Terminal=false
Categories=Game;Utility;
EOF

echo ""
echo "Done. You can open it two ways:"
echo "  - Search for 'Cascabel Covers' in the Cinnamon menu"
echo "  - Run: cascabel-covers   (if ~/.local/bin is in your PATH)"
echo ""
echo "To uninstall, open the app and use the 'Uninstall' button."
