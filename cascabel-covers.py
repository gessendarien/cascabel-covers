#!/usr/bin/env python3
"""
Cascabel Covers
Applies each game's box art (NES, SNES, N64, GameCube, Wii, Wii U, PS1, PS2, Xbox, etc.) as the file icon
for the matching ROM file in Nemo (Linux Mint Cinnamon).

Cover art source: public libretro-thumbnails repositories
(the same ones RetroArch uses), downloaded and cached locally.
"""
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk, Gio

import os
import locale
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
STATS_PATH = os.path.join(BASE_DIR, "stats.json")
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
CANCEL_SCAN = False
DESKTOP_FILE = os.path.expanduser("~/.local/share/applications/cascabel-covers.desktop")
BIN_LINK = os.path.expanduser("~/.local/bin/cascabel-covers")

# ---------------------------------------------------------------------------
# Supported systems -> libretro-thumbnails repo
# ---------------------------------------------------------------------------
SYSTEMS = {
    ".nes": [{"repo": "Nintendo_-_Nintendo_Entertainment_System", "label": "NES"}],
    ".sfc": [{"repo": "Nintendo_-_Super_Nintendo_Entertainment_System", "label": "SNES"}],
    ".smc": [{"repo": "Nintendo_-_Super_Nintendo_Entertainment_System", "label": "SNES"}],
    ".n64": [{"repo": "Nintendo_-_Nintendo_64", "label": "N64"}],
    ".z64": [{"repo": "Nintendo_-_Nintendo_64", "label": "N64"}],
    ".v64": [{"repo": "Nintendo_-_Nintendo_64", "label": "N64"}],
    ".gcm": [{"repo": "Nintendo_-_GameCube", "label": "GameCube"}],
    ".rvz": [{"repo": "Nintendo_-_GameCube", "label": "GameCube"}, {"repo": "Nintendo_-_Wii", "label": "Wii"}],
    ".ciso": [{"repo": "Nintendo_-_GameCube", "label": "GameCube"}],
    ".wbfs": [{"repo": "Nintendo_-_Wii", "label": "Wii"}],
    ".wia": [{"repo": "Nintendo_-_Wii", "label": "Wii"}],
    ".wud": [{"repo": "Nintendo_-_Wii_U", "label": "Wii U"}],
    ".wux": [{"repo": "Nintendo_-_Wii_U", "label": "Wii U"}],
    ".rpx": [{"repo": "Nintendo_-_Wii_U", "label": "Wii U"}],
    ".cue": [{"repo": "Sony_-_PlayStation", "label": "PS1"}, {"repo": "Sega_-_Saturn", "label": "Saturn"}],
    ".pbp": [{"repo": "Sony_-_PlayStation", "label": "PS1"}, {"repo": "Sony_-_PlayStation_Portable", "label": "PSP"}],
    ".cso": [{"repo": "Sony_-_PlayStation_Portable", "label": "PSP"}, {"repo": "Sony_-_PlayStation_2", "label": "PS2"}],
    ".bin": [{"repo": "Sony_-_PlayStation", "label": "PS1"}, {"repo": "Sony_-_PlayStation_2", "label": "PS2"}],
    ".xbe": [{"repo": "Microsoft_-_Xbox", "label": "Xbox"}],
    ".xex": [{"repo": "Microsoft_-_Xbox_360", "label": "Xbox 360"}],
    ".cdi": [{"repo": "Sega_-_Dreamcast", "label": "Dreamcast"}],
    ".gdi": [{"repo": "Sega_-_Dreamcast", "label": "Dreamcast"}],
    ".gb": [{"repo": "Nintendo_-_Game_Boy", "label": "GB"}],
    ".gbc": [{"repo": "Nintendo_-_Game_Boy_Color", "label": "GBC"}],
    ".gba": [{"repo": "Nintendo_-_Game_Boy_Advance", "label": "GBA"}],
    ".nds": [{"repo": "Nintendo_-_Nintendo_DS", "label": "DS"}],
    ".3ds": [{"repo": "Nintendo_-_Nintendo_3DS", "label": "3DS"}],
    ".cia": [{"repo": "Nintendo_-_Nintendo_3DS", "label": "3DS"}],
    ".cci": [{"repo": "Nintendo_-_Nintendo_3DS", "label": "3DS"}],
    ".iso": [
        {"repo": "Sony_-_PlayStation_2", "label": "PS2"},
        {"repo": "Sony_-_PlayStation_Portable", "label": "PSP"},
        {"repo": "Nintendo_-_Wii", "label": "Wii"},
        {"repo": "Nintendo_-_GameCube", "label": "GameCube"},
        {"repo": "Sony_-_PlayStation", "label": "PS1"},
        {"repo": "Microsoft_-_Xbox", "label": "Xbox"},
        {"repo": "Microsoft_-_Xbox_360", "label": "Xbox 360"}
    ],
    ".chd": [
        {"repo": "Sony_-_PlayStation_2", "label": "PS2"},
        {"repo": "Sony_-_PlayStation", "label": "PS1"},
        {"repo": "Sega_-_Dreamcast", "label": "Dreamcast"}
    ],
    ".zip": [
        {"repo": "MAME", "label": "MAME"},
        {"repo": "Nintendo_-_Nintendo_Entertainment_System", "label": "NES"},
        {"repo": "Nintendo_-_Super_Nintendo_Entertainment_System", "label": "SNES"},
        {"repo": "Nintendo_-_Nintendo_64", "label": "N64"},
        {"repo": "Nintendo_-_Game_Boy", "label": "GB"},
        {"repo": "Nintendo_-_Game_Boy_Color", "label": "GBC"},
        {"repo": "Nintendo_-_Game_Boy_Advance", "label": "GBA"},
        {"repo": "Sega_-_Mega_Drive_-_Genesis", "label": "Genesis"}
    ],
    ".7z": [{"repo": "MAME", "label": "MAME"}]
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

def extract_tags(s):
    tags = re.findall(r"[\(\[](.*?)[\)\]]", s)
    res = set()
    for t in tags:
        t_low = t.lower()
        if t_low == "u": res.add("usa")
        elif t_low == "e": res.add("europe")
        elif t_low == "j" or t_low == "jp": res.add("japan")
        else: res.add(t_low)
    return res

def find_best_match(rom_title, titles):
    rom_norm = _normalize(rom_title)
    rom_tags = extract_tags(rom_title)
    
    best, best_score = None, 0.0
    for t in titles:
        t_norm = _normalize(t)
        
        if rom_norm == t_norm:
            base_score = 1.0
        elif rom_norm in t_norm:
            base_score = 0.85 + 0.15 * (len(rom_norm) / len(t_norm))
        elif t_norm in rom_norm:
            base_score = 0.85 + 0.15 * (len(t_norm) / len(rom_norm))
        else:
            base_score = difflib.SequenceMatcher(None, rom_norm, t_norm).ratio()
        
        if base_score < 0.65:
            continue
            
        t_tags = extract_tags(t)
        tag_score = 0.0
        
        if rom_tags:
            overlap = len(rom_tags.intersection(t_tags))
            tag_score += overlap * 0.1
            tag_score -= len(t_tags - rom_tags) * 0.01
        else:
            # If ROM has no region tags, prioritize USA then Japan
            if any("usa" in tag for tag in t_tags):
                tag_score += 0.05
            elif any("japan" in tag for tag in t_tags):
                tag_score += 0.02
            
            # Penalize all extra tags so we prefer the cleanest release over demos/betas
            tag_score -= len(t_tags) * 0.01
                
        score = base_score + tag_score
        if score > best_score:
            best_score, best = score, t
            
    if best_score >= 0.65:
        return best, best_score
    return None, best_score

def download_cover(repo, title):
    local_dir = os.path.join(COVERS_DIR, repo)
    os.makedirs(local_dir, exist_ok=True)
    safe_name = title.replace("/", "_") + ".png"
    local_path = os.path.join(local_dir, safe_name)
    
    if os.path.exists(local_path) and os.path.getsize(local_path) > 300:
        return local_path

    def _fetch(t, save_path, depth=0):
        if depth > 3: raise Exception("Too many symlinks")
        url = RAW_BASE.format(repo=repo) + urllib.parse.quote(t + ".png")
        req = urllib.request.Request(url, headers=UA_HEADERS)
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
            # GitHub raw symlinks are just plain text containing the target filename
            if len(data) < 300 and data.strip().endswith(b".png"):
                target = data.decode("utf-8").strip()[:-4]
                return _fetch(target, save_path, depth + 1)
            
            with open(save_path, "wb") as f:
                f.write(data)
        return save_path

    return _fetch(title, local_path)

# ---------------------------------------------------------------------------
# Apply / revert the file icon (via GVFS metadata, same thing Nemo uses)
# ---------------------------------------------------------------------------
def apply_icon(file_path, cover_path):
    try:
        uri = "file://" + urllib.parse.quote(os.path.abspath(cover_path))
        f = Gio.File.new_for_path(file_path)
        f.set_attribute_string("metadata::custom-icon", uri, Gio.FileQueryInfoFlags.NONE, None)
    except Exception:
        pass

def revert_icon(file_path):
    subprocess.run(
        ["gio", "set", "-t", "unset", file_path, "metadata::custom-icon"],
        check=False, capture_output=True,
    )

def refresh_nemo():
    subprocess.run(["nemo", "-q"], check=False, capture_output=True)

# ---------------------------------------------------------------------------

def load_stats():
    if os.path.exists(STATS_PATH):
        with open(STATS_PATH) as f:
            return json.load(f)
    return {"applied": 0, "failed": 0}

def save_stats(applied, failed):
    os.makedirs(BASE_DIR, exist_ok=True)
    with open(STATS_PATH, "w") as f:
        json.dump({"applied": applied, "failed": failed}, f)


def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            c = json.load(f)
            c["first_time"] = False
            return c
    return {"roms_path": "", "first_time": True}

def save_config(conf):
    os.makedirs(BASE_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(conf, f)

# Main scan
# ---------------------------------------------------------------------------
def scan_and_apply(status_cb, force_rescan=False, lang_dict=None):
    global CANCEL_SCAN
    registry = load_registry()
    applied = skipped = failed = 0
    index_cache = {}
    failed_log = []
    
    root = load_config().get("roms_path", os.path.expanduser("~"))
    for dirpath, dirnames, filenames in os.walk(root):
        if CANCEL_SCAN:
            break
            
        # Skip hidden directories
        dirnames[:] = [d for d in dirnames if not d.startswith('.')]
        
        for fn in filenames:
            if CANCEL_SCAN:
                break
            ext = os.path.splitext(fn)[1].lower()
            if ext not in SYSTEMS:
                continue
            full = os.path.join(dirpath, fn)
            if not force_rescan and full in registry and os.path.exists(registry[full]):
                apply_icon(full, registry[full])
                skipped += 1
                continue

            candidates = SYSTEMS[ext]
            best_match = None
            best_score = 0
            best_repo = None
            
            for info in candidates:
                if CANCEL_SCAN:
                    break
                repo = info["repo"]
                if repo not in index_cache:
                    cache_file = os.path.join(COVERS_DIR, f"index_{repo}.json")
                    is_cached = os.path.exists(cache_file) and (time.time() - os.path.getmtime(cache_file) < 30 * 24 * 3600)
                    if is_cached:
                        if status_cb:
                            msg = lang_dict["applying"].format(system=info["label"]) if lang_dict else f"Applying {info['label']} covers..."
                            status_cb(msg)
                    else:
                        if status_cb:
                            msg = lang_dict["downloading"].format(system=info["label"]) if lang_dict else f"Downloading {info['label']} index..."
                            status_cb(msg)
                    try:
                        index_cache[repo] = get_index(repo)
                    except Exception:
                        index_cache[repo] = []

                titles = index_cache[repo]
                rom_title = os.path.splitext(fn)[0]
                m, s = find_best_match(rom_title, titles)
                if m and s > best_score:
                    best_match = m
                    best_score = s
                    best_repo = repo
            
            if CANCEL_SCAN:
                break
                
            if not best_match:
                failed += 1
                failed_log.append(f"NOT FOUND (Low similarity or missing in DB): {fn}")
                continue

            try:
                cover_path = download_cover(best_repo, best_match)
                apply_icon(full, cover_path)
                registry[full] = cover_path
                applied += 1
            except Exception as e:
                failed += 1
                failed_log.append(f"FAILED (Download/Apply Error): {fn} - {str(e)}")

    # Write the failed log
    log_path = os.path.join(BASE_DIR, "missing.log")
    if failed_log:
        with open(log_path, "w") as f:
            f.write("\n".join(failed_log))
    elif os.path.exists(log_path):
        os.remove(log_path)

    save_registry(registry)
    save_stats(applied, failed)
    refresh_nemo()
    return applied, skipped, failed

def revert_all():
    registry = load_registry()
    for path in list(registry.keys()):
        if os.path.exists(path):
            revert_icon(path)
    save_registry({})
    save_stats(0, 0)
    refresh_nemo()

# ---------------------------------------------------------------------------
# GUI
# ---------------------------------------------------------------------------

def get_strings():
    try:
        lang, _ = locale.getlocale()
        if not lang:
            lang, _ = locale.getdefaultlocale()
    except Exception:
        lang = "en"
    
    if lang and lang.startswith('es'):
        return {
            "active": "Monitoreo Activo",
            "inactive": "Monitoreo Inactivo",
            "working": "Trabajando...",
            "scanning": "Escaneando...",
            "uninstalling": "Desinstalando...",
            "applied": "aplicado",
            "not_found": "no encontrados",
            "scan_btn": "ESCANEAR DE NUEVO",
            "uninstall_btn": "DESINSTALAR",
            "dialog_title": "¿Desinstalar Cascabel Covers?",
            "dialog_text": "¿Estás seguro? Esto revertirá todas las carátulas aplicadas y eliminará el caché.",
            "applying": "Aplicando carátulas de {system}...",
            "downloading": "Descargando índice de {system}...",
            "folder_btn_tooltip": "Cambiar carpeta de ROMs",
            "no_folder": "Ninguna carpeta seleccionada",
            "select_first": "Elige primero una carpeta de juegos",
            "roms_folder_label": "Carpeta de juegos a escanear:"
        }
    else:
        return {
            "active": "Active Monitoring",
            "inactive": "Inactive Monitoring",
            "working": "Working...",
            "scanning": "Scanning...",
            "uninstalling": "Uninstalling...",
            "applied": "applied",
            "not_found": "not found",
            "scan_btn": "SCAN AGAIN",
            "uninstall_btn": "UNINSTALL",
            "dialog_title": "Uninstall Cascabel Covers?",
            "dialog_text": "Are you sure? This will revert all applied covers and delete your cache.",
            "applying": "Applying {system} covers...",
            "downloading": "Downloading {system} index...",
            "folder_btn_tooltip": "Change ROMs folder",
            "no_folder": "No folder selected",
            "select_first": "Select a games folder first",
            "roms_folder_label": "Games folder to scan:"
        }

class CascabelCoversWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="Cascabel Covers")
        self.set_border_width(20)
        self.set_default_size(350, -1)
        self.set_resizable(False)
        self.get_style_context().add_class("main-window")

        self.working = False
        self.strings = get_strings()

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        self.add(outer)

        # Top Card
        card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
        card.get_style_context().add_class("card")
        
        # Switch
        self.switch = Gtk.Switch()
        self.switch.set_active(bool(load_registry()))
        self.switch.connect("state-set", self.on_switch_toggled)
        self.switch.set_valign(Gtk.Align.CENTER)
        card.pack_start(self.switch, False, False, 0)
        
        # Text Column
        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        text_box.set_valign(Gtk.Align.CENTER)
        
        self.title_label = Gtk.Label(label=self.strings["active"] if self.switch.get_active() else self.strings["inactive"])
        self.title_label.set_xalign(0)
        self.title_label.get_style_context().add_class("title-label")
        
        stats = load_stats()
        self.subtitle_label = Gtk.Label(label=f"{stats['applied']} {self.strings['applied']} | {stats['failed']} {self.strings['not_found']}")
        self.subtitle_label.set_xalign(0)
        self.subtitle_label.get_style_context().add_class("subtitle-label")
        
        text_box.pack_start(self.title_label, False, False, 0)
        text_box.pack_start(self.subtitle_label, False, False, 0)
        card.pack_start(text_box, True, True, 0)
        
        # Action Area
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        action_box.set_valign(Gtk.Align.CENTER)
        
        self.icon_btn = Gtk.Button()
        icon = Gtk.Image.new_from_icon_name("view-refresh-symbolic", Gtk.IconSize.BUTTON)
        self.icon_btn.set_image(icon)
        self.icon_btn.get_style_context().add_class("refresh-btn")
        self.icon_btn.connect("clicked", self.on_rescan)
        
        self.spinner = Gtk.Spinner()
        self.spinner.set_no_show_all(True)
        
        action_box.pack_end(self.icon_btn, False, False, 0)
        action_box.pack_end(self.spinner, False, False, 0)
        card.pack_end(action_box, False, False, 0)
        
        
        outer.pack_start(card, False, False, 0)
        
        # Folder Selector Button
        self.config = load_config()
        self.folder_btn = Gtk.Button()
        self.folder_btn.set_tooltip_text(self.strings["folder_btn_tooltip"])
        self.folder_btn.get_style_context().add_class("folder-btn")
        
        # Folder Section Group
        folder_section_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        
        # Folder Title
        self.folder_title_label = Gtk.Label(label=self.strings["roms_folder_label"])
        self.folder_title_label.set_halign(Gtk.Align.START)
        folder_section_box.pack_start(self.folder_title_label, False, False, 0)
        
        # Warning label (below title, above button)
        self.warning_label = Gtk.Label(label="")
        self.warning_label.set_halign(Gtk.Align.CENTER)
        self.warning_label.get_style_context().add_class("warning-label")
        folder_section_box.pack_start(self.warning_label, False, False, 0)
        
        folder_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        folder_box.set_halign(Gtk.Align.CENTER)
        
        folder_icon = Gtk.Image.new_from_icon_name("folder-symbolic", Gtk.IconSize.BUTTON)
        initial_label = self.shorten_path(self.config["roms_path"]) if self.config["roms_path"] else self.strings["no_folder"]
        self.folder_label = Gtk.Label(label=initial_label)
        self.folder_label.set_ellipsize(3) # Pango.EllipsizeMode.END (3)
        self.folder_label.set_max_width_chars(30)
        
        folder_box.pack_start(folder_icon, False, False, 0)
        folder_box.pack_start(self.folder_label, False, False, 0)
        self.folder_btn.add(folder_box)
        self.folder_btn.connect("clicked", self.on_folder_clicked)
        
        folder_section_box.pack_start(self.folder_btn, False, False, 0)
        outer.pack_start(folder_section_box, False, False, 0)
        
        # Uninstall Button
        uninstall_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        uninstall_box.set_halign(Gtk.Align.CENTER)
        
        uninstall_icon = Gtk.Image.new_from_icon_name("user-trash-symbolic", Gtk.IconSize.BUTTON)
        uninstall_label = Gtk.Label(label=self.strings["uninstall_btn"])
        
        self.uninstall_btn = Gtk.Button()
        self.uninstall_btn.get_style_context().add_class("uninstall-btn")
        self.uninstall_btn.add(uninstall_box)
        uninstall_box.pack_start(uninstall_icon, False, False, 0)
        uninstall_box.pack_start(uninstall_label, False, False, 0)
        self.uninstall_btn.connect("clicked", self.on_uninstall)
        
        outer.pack_start(self.uninstall_btn, False, False, 0)
        
        # Footer
        footer = Gtk.Label(label="BY GESSÉN DARIÉN 0.0.1")
        footer.get_style_context().add_class("footer-label")
        footer.set_margin_top(10)
        outer.pack_end(footer, False, False, 0)

        self.connect("destroy", Gtk.main_quit)

        if "--auto-scan" in sys.argv and self.config["roms_path"]:
            GLib.idle_add(self.on_rescan, None)

    def shorten_path(self, path):
        home = os.path.expanduser("~")
        if path.startswith(home):
            return "~" + path[len(home):]
        return path

    def on_folder_clicked(self, _btn):
        dialog = Gtk.FileChooserDialog(
            title=self.strings["folder_btn_tooltip"],
            parent=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.OK,
        )
        dialog.set_current_folder(self.config["roms_path"])
        
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            selected = dialog.get_filename()
            self.config["roms_path"] = selected
            self.config["first_time"] = False
            save_config(self.config)
            self.folder_label.set_text(self.shorten_path(selected))
            self.warning_label.set_text("")
            
        dialog.destroy()

    def update_ui_state(self, active, msg=None):
        self.title_label.set_text(self.strings["active"] if active else self.strings["inactive"])
        if msg:
            self.subtitle_label.set_text(msg)

    def set_status_threadsafe(self, msg):
        GLib.idle_add(self.subtitle_label.set_text, msg)

    # -- switch ---------------------------------------------------------------
    def on_switch_toggled(self, switch, state):
        if self.working:
            return False

        if state and not self.config["roms_path"]:
            GLib.idle_add(switch.set_active, False)
            return True

        global CANCEL_SCAN
        CANCEL_SCAN = False
        self.working = True
        switch.set_sensitive(False)
        self.icon_btn.set_image(Gtk.Image.new_from_icon_name("media-playback-stop-symbolic", Gtk.IconSize.BUTTON))
        self.icon_btn.show()
        self.folder_btn.set_sensitive(False)
        self.spinner.show()
        self.spinner.start()
        self.title_label.set_text(self.strings["working"])

        def worker():
            if state:
                applied, skipped, failed = scan_and_apply(self.set_status_threadsafe, lang_dict=self.strings)
                summary = f"{applied} {self.strings['applied']} | {failed} {self.strings['not_found']}"
            else:
                revert_all()
                summary = f"0 {self.strings['applied']} | 0 {self.strings['not_found']}"
            GLib.idle_add(self.update_ui_state, state, summary)
            GLib.idle_add(self._finish_toggle, state)

        threading.Thread(target=worker, daemon=True).start()
        return False

    def _finish_toggle(self, state):
        self.working = False
        self.switch.set_sensitive(True)
        self.spinner.stop()
        self.spinner.hide()
        self.icon_btn.set_image(Gtk.Image.new_from_icon_name("view-refresh-symbolic", Gtk.IconSize.BUTTON))
        self.icon_btn.show()
        self.folder_btn.set_sensitive(True)

    # -- rescan ---------------------------------------------------------
    def on_rescan(self, _btn):
        global CANCEL_SCAN
        if not self.config["roms_path"]:
            self.warning_label.set_text(self.strings["select_first"])
            self.switch.set_active(False)
            return
            
        self.warning_label.set_text("")
        if self.working:
            CANCEL_SCAN = True
            return
            
        CANCEL_SCAN = False
        self.working = True
        self.switch.set_active(True)
        self.switch.set_sensitive(False)
        self.icon_btn.set_image(Gtk.Image.new_from_icon_name("media-playback-stop-symbolic", Gtk.IconSize.BUTTON))
        self.icon_btn.show()
        self.folder_btn.set_sensitive(False)
        self.spinner.show()
        self.spinner.start()
        self.title_label.set_text(self.strings["scanning"])
        
        def worker():
            applied, skipped, failed = scan_and_apply(self.set_status_threadsafe, force_rescan=True, lang_dict=self.strings)
            summary = f"{applied} {self.strings['applied']} | {failed} {self.strings['not_found']}"
            GLib.idle_add(self.update_ui_state, True, summary)
            GLib.idle_add(self.switch.set_active, True)
            GLib.idle_add(self._finish_toggle, True)
            
        threading.Thread(target=worker, daemon=True).start()

    # -- uninstall ------------------------------------------------------
    def on_uninstall(self, _btn):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.YES_NO,
            text=self.strings["dialog_title"],
        )
        dialog.format_secondary_text(
            self.strings["dialog_text"]
        )
        response = dialog.run()
        dialog.destroy()
        if response != Gtk.ResponseType.YES:
            return

        self.title_label.set_text(self.strings["uninstalling"])
        self.switch.set_sensitive(False)
        self.folder_btn.set_sensitive(False)

        def worker():
            revert_all()
            shutil.rmtree(BASE_DIR, ignore_errors=True)
            for path in (DESKTOP_FILE, BIN_LINK):
                if os.path.islink(path) or os.path.exists(path):
                    try:
                        os.remove(path)
                    except OSError:
                        pass
            GLib.idle_add(Gtk.main_quit)

        threading.Thread(target=worker, daemon=True).start()

def main():
    css = b'''
    window.main-window {
        background-color: #1e1e1e;
    }
    .card {
        background-color: #161616;
        border-radius: 12px;
        padding: 16px;
    }
    .title-label {
        color: #ffffff;
        font-weight: bold;
        font-size: 16px;
    }
    .subtitle-label {
        color: #aaaaaa;
        font-size: 12px;
    }
    .warning-label {
        color: #ff5555;
        font-size: 12px;
        font-weight: bold;
    }
    .folder-btn {
        background-color: #242424;
        color: #cccccc;
        border-radius: 8px;
        padding: 8px 12px;
        border: 1px solid #333333;
    }
    .folder-btn:hover {
        background-color: #2c2c2c;
        color: #ffffff;
    }
    .refresh-btn {
        background: transparent;
        color: #aaaaaa;
        border: none;
        box-shadow: none;
    }
    .refresh-btn:hover {
        color: #ffffff;
    }
    .big-button {
        background-color: #333333;
        color: #ffffff;
        border-radius: 10px;
        padding: 12px;
        border: none;
        font-weight: bold;
    }
    .big-button:hover {
        background-color: #444444;
    }
    .uninstall-btn {
        color: #d17575;
        background: transparent;
        border: none;
        box-shadow: none;
    }
    .uninstall-btn:hover {
        color: #ff8b8b;
    }
    .footer-label {
        color: #555555;
        font-size: 10px;
        letter-spacing: 2px;
    }
    '''
    css_provider = Gtk.CssProvider()
    css_provider.load_from_data(css)
    context = Gtk.StyleContext()
    screen = Gdk.Screen.get_default()
    context.add_provider_for_screen(screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    if "--auto" in sys.argv:
        print("Cascabel Covers: Running automatic scan...")
        def cli_status(msg):
            print(f"[*] {msg}")
        applied, skipped, failed = scan_and_apply(cli_status)
        print(f"Scan complete: {applied} applied, {failed} not found.")
        sys.exit(0)

    win = CascabelCoversWindow()
    win.show_all()
    Gtk.main()

if __name__ == "__main__":
    main()
