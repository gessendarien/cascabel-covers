#!/usr/bin/env python3
"""
Cascabel Covers
Applies each game's box art (NES / SNES / N64) as the file icon
for the matching ROM file in Nemo (Linux Mint Cinnamon).

Cover art source: public libretro-thumbnails repositories
(the same ones RetroArch uses), downloaded and cached locally.
"""
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

import os
import re
import sys
import json
import time
import shutil
import difflib
import threading
import subprocess
import urllib.request
import urllib.parse

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.expanduser("~/.cascabel-covers")
COVERS_DIR = os.path.join(BASE_DIR, "covers")
REGISTRY_PATH = os.path.join(BASE_DIR, "registry.json")
DESKTOP_FILE = os.path.expanduser("~/.local/share/applications/cascabel-covers.desktop")
BIN_LINK = os.path.expanduser("~/.local/bin/cascabel-covers")

# ---------------------------------------------------------------------------
# Supported systems -> libretro-thumbnails repo
# ---------------------------------------------------------------------------
SYSTEMS = {
    ".nes": {"repo": "Nintendo_-_Nintendo_Entertainment_System", "label": "NES"},
    ".sfc": {"repo": "Nintendo_-_Super_Nintendo_Entertainment_System", "label": "SNES"},
    ".smc": {"repo": "Nintendo_-_Super_Nintendo_Entertainment_System", "label": "SNES"},
    ".n64": {"repo": "Nintendo_-_Nintendo_64", "label": "N64"},
    ".z64": {"repo": "Nintendo_-_Nintendo_64", "label": "N64"},
    ".v64": {"repo": "Nintendo_-_Nintendo_64", "label": "N64"},
}

RAW_BASE = "https://raw.githubusercontent.com/libretro-thumbnails/{repo}/master/Named_Boxarts/"
API_TREE = "https://api.github.com/repos/libretro-thumbnails/{repo}/git/trees/master?recursive=1"

UA_HEADERS = {"User-Agent": "cascabel-covers"}

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
def load_registry():
    if os.path.exists(REGISTRY_PATH):
        with open(REGISTRY_PATH) as f:
            return json.load(f)
    return {}

def save_registry(reg):
    os.makedirs(BASE_DIR, exist_ok=True)
    with open(REGISTRY_PATH, "w") as f:
        json.dump(reg, f, indent=2)

# ---------------------------------------------------------------------------
# Index of available cover art per system (cached for 30 days)
# ---------------------------------------------------------------------------
def get_index(repo):
    cache_file = os.path.join(COVERS_DIR, f"index_{repo}.json")
    if os.path.exists(cache_file):
        age = time.time() - os.path.getmtime(cache_file)
        if age < 30 * 24 * 3600:
            with open(cache_file) as f:
                return json.load(f)

    url = API_TREE.format(repo=repo)
    req = urllib.request.Request(url, headers=UA_HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)

    titles = []
    for item in data.get("tree", []):
        path = item.get("path", "")
        if path.startswith("Named_Boxarts/") and path.endswith(".png"):
            titles.append(path[len("Named_Boxarts/"):-4])

    os.makedirs(COVERS_DIR, exist_ok=True)
    with open(cache_file, "w") as f:
        json.dump(titles, f)
    return titles

def _normalize(s):
    s = s.lower()
    s = re.sub(r"[\(\[].*?[\)\]]", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return s.strip()

def find_best_match(rom_title, titles):
    rom_norm = _normalize(rom_title)
    best, best_score = None, 0.0
    for t in titles:
        score = difflib.SequenceMatcher(None, rom_norm, _normalize(t)).ratio()
        if score > best_score:
            best_score, best = score, t
    if best_score >= 0.55:
        return best, best_score
    return None, best_score

def download_cover(repo, title):
    local_dir = os.path.join(COVERS_DIR, repo)
    os.makedirs(local_dir, exist_ok=True)
    safe_name = title.replace("/", "_") + ".png"
    local_path = os.path.join(local_dir, safe_name)
    if os.path.exists(local_path):
        return local_path

    url = RAW_BASE.format(repo=repo) + urllib.parse.quote(title + ".png")
    req = urllib.request.Request(url, headers=UA_HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r, open(local_path, "wb") as f:
        shutil.copyfileobj(r, f)
    return local_path

# ---------------------------------------------------------------------------
# Apply / revert the file icon (via GVFS metadata, same thing Nemo uses)
# ---------------------------------------------------------------------------
def apply_icon(file_path, cover_path):
    uri = "file://" + urllib.parse.quote(os.path.abspath(cover_path))
    subprocess.run(
        ["gio", "set", "-t", "string", file_path, "metadata::custom-icon", uri],
        check=False, capture_output=True,
    )

def revert_icon(file_path):
    subprocess.run(
        ["gio", "set", "-t", "unset", file_path, "metadata::custom-icon"],
        check=False, capture_output=True,
    )

def refresh_nemo():
    subprocess.run(["nemo", "-q"], check=False, capture_output=True)

# ---------------------------------------------------------------------------
# Main scan
# ---------------------------------------------------------------------------
def scan_and_apply(status_cb):
    registry = load_registry()
    applied = skipped = failed = 0
    index_cache = {}
    
    root = os.path.expanduser("~")
    for dirpath, dirnames, filenames in os.walk(root):
        # Skip hidden directories
        dirnames[:] = [d for d in dirnames if not d.startswith('.')]
        
        for fn in filenames:
            ext = os.path.splitext(fn)[1].lower()
            if ext not in SYSTEMS:
                continue
            full = os.path.join(dirpath, fn)
            if full in registry and os.path.exists(registry[full]):
                skipped += 1
                continue

            info = SYSTEMS[ext]
            repo = info["repo"]
            if repo not in index_cache:
                cache_file = os.path.join(COVERS_DIR, f"index_{repo}.json")
                is_cached = os.path.exists(cache_file) and (time.time() - os.path.getmtime(cache_file) < 30 * 24 * 3600)
                if is_cached:
                    status_cb(f"Applying {info['label']} covers...")
                else:
                    status_cb(f"Downloading {info['label']} index...")
                try:
                    index_cache[repo] = get_index(repo)
                except Exception:
                    index_cache[repo] = []

            titles = index_cache[repo]
            rom_title = os.path.splitext(fn)[0]
            match, score = find_best_match(rom_title, titles)
            if not match:
                failed += 1
                continue

            try:
                cover_path = download_cover(repo, match)
                apply_icon(full, cover_path)
                registry[full] = cover_path
                applied += 1
            except Exception:
                failed += 1

    save_registry(registry)
    refresh_nemo()
    return applied, skipped, failed

def revert_all():
    registry = load_registry()
    for path in list(registry.keys()):
        if os.path.exists(path):
            revert_icon(path)
    save_registry({})
    refresh_nemo()

# ---------------------------------------------------------------------------
# GUI
# ---------------------------------------------------------------------------
class CascabelCoversWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="Cascabel Covers")
        self.set_border_width(14)
        self.set_default_size(320, -1)
        self.set_resizable(False)

        self.working = False

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        self.add(outer)

        # Title
        title = Gtk.Label()
        title.set_markup("<b>Cascabel Covers</b>")
        title.set_xalign(0)
        outer.pack_start(title, False, False, 0)

        # Active / Inactive switch & Status
        switch_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.switch = Gtk.Switch()
        self.switch.set_active(bool(load_registry()))
        self.switch.connect("state-set", self.on_switch_toggled)
        self.state_label = Gtk.Label(label=self._state_text(self.switch.get_active()))
        
        switch_box.pack_start(self.switch, False, False, 0)
        switch_box.pack_start(self.state_label, False, False, 0)
        outer.pack_start(switch_box, False, False, 0)

        outer.pack_start(Gtk.Separator(), False, False, 4)

        # Bottom buttons / Link
        bottom_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        
        github_link = Gtk.LinkButton(uri="https://github.com/gessendarien/cascabel-covers", label="By Gessén Darién")
        bottom_box.pack_start(github_link, False, False, 0)
        
        uninstall_btn = Gtk.Button(label="Uninstall")
        uninstall_btn.get_style_context().add_class("destructive-action")
        uninstall_btn.connect("clicked", self.on_uninstall)
        bottom_box.pack_end(uninstall_btn, False, False, 0)
        
        outer.pack_start(bottom_box, False, False, 0)

        self.connect("destroy", Gtk.main_quit)

    def _state_text(self, active):
        return "Active" if active else "Inactive"

    def set_status_threadsafe(self, msg):
        GLib.idle_add(self.state_label.set_text, msg)

    # -- switch ---------------------------------------------------------------
    def on_switch_toggled(self, switch, state):
        if self.working:
            return True  # ignore clicks while busy

        self.working = True
        switch.set_sensitive(False)
        self.state_label.set_text("Working...")

        def worker():
            if state:
                applied, skipped, failed = scan_and_apply(self.set_status_threadsafe)
                summary = f"Done: {applied} applied, {failed} not found."
            else:
                revert_all()
                summary = "Inactive"
            self.set_status_threadsafe(summary)
            GLib.idle_add(self._finish_toggle, state)

        threading.Thread(target=worker, daemon=True).start()
        return False  # let the switch visually change state

    def _finish_toggle(self, state):
        self.working = False
        self.switch.set_sensitive(True)

    # -- uninstall ------------------------------------------------------
    def on_uninstall(self, _btn):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.WARNING,
            text="Uninstall Cascabel Covers?",
        )
        dialog.format_secondary_text(
            "Do you want to revert all applied covers, or keep them applied to your ROMs? (Keeping them leaves the cache intact)."
        )
        dialog.add_buttons(
            "Cancel", Gtk.ResponseType.CANCEL,
            "Keep Covers", Gtk.ResponseType.NO,
            "Remove Completely", Gtk.ResponseType.YES
        )
        response = dialog.run()
        dialog.destroy()
        if response == Gtk.ResponseType.CANCEL or response == Gtk.ResponseType.DELETE_EVENT:
            return

        self.state_label.set_text("Uninstalling...")
        self.switch.set_sensitive(False)

        def worker():
            if response == Gtk.ResponseType.YES:
                revert_all()
                shutil.rmtree(BASE_DIR, ignore_errors=True)
            else:
                if os.path.exists(REGISTRY_PATH):
                    try:
                        os.remove(REGISTRY_PATH)
                    except OSError:
                        pass
                        
            for path in (DESKTOP_FILE, BIN_LINK):
                if os.path.islink(path) or os.path.exists(path):
                    try:
                        os.remove(path)
                    except OSError:
                        pass
            GLib.idle_add(Gtk.main_quit)

        threading.Thread(target=worker, daemon=True).start()

def main():
    win = CascabelCoversWindow()
    win.show_all()
    Gtk.main()

if __name__ == "__main__":
    main()
