# Cascabel Covers

**Version**: 0.0.1
**OS**: Linux Mint (Cinnamon / Nemo)  
**License**: GPL  

Cascabel Covers automatically applies box art to your retro ROMs (NES, SNES, N64, GameCube, Wii, PS1, PS2, Xbox, etc). It scans your game folder and downloads the correct cover art from the libretro-thumbnails repository, setting it as the custom file icon in the Nemo file manager.

*Note: This application is designed specifically for the Linux Mint Cinnamon edition, as it relies on its default file manager (Nemo) to properly apply and refresh the custom icons.*

---

## 🖼️ Screenshots

![Main Interface](assets/screenshot-main.png)
*(Image Field: Main App Interface)*

![Covers in Nemo](assets/screenshot-nemo.png)
*(Image Field: ROMs with covers applied in Nemo)*

---

## ⚙️ Installation

To install Cascabel Covers, you just need to run the `install.sh` script.

**Important:** Before running it, make sure the script has execution permissions. You can do this in two ways:
- **Graphically:** Right-click on `install.sh` -> **Properties** -> **Permissions** -> Check the box **"Allow executing file as program"**. Then double click it and select "Run in Terminal" or "Run".
- **Using the Terminal:**
  ```bash
  chmod +x install.sh
  ./install.sh
  ```

---

## 🚀 Usage

1. Open **Cascabel Covers** from your system's application menu.
2. Click the folder button to select the directory where your games are located.
3. Click the **Scan (Arrow)** button to start downloading and applying covers to all your games.

**How to Deactivate:**
If you want to temporarily deactivate the covers and restore your default icons *without* uninstalling the app:
1. Open the app and simply click the **Main Switch** to turn it gray. 
2. All custom icons will be instantly removed. 
3. Click the switch again if you want to reactivate them and restore all your covers instantly!
