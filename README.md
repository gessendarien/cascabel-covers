# Cascabel Covers

**Version**: 0.0.1  
**OS**: Linux Mint (Cinnamon / Nemo)  
**License**: GPL  

Cascabel Covers automatically applies box art to your retro ROMs (NES, SNES, N64, GameCube, Wii, PS1, PS2, Xbox, etc). It scans your home folder and downloads the correct cover art from the libretro-thumbnails repository, setting it as the custom file icon in the Nemo file manager. Covers are cached in `~/.cascabel-covers/covers/`.

*Note: This application is designed specifically for the Linux Mint Cinnamon edition, as it relies on its default file manager (Nemo) to properly apply and refresh the custom icons.*

### Installation

1. Make the install script executable:
   ```bash
   chmod +x install.sh
   ```
2. Run the installer:
   ```bash
   ./install.sh
   ```

The installer will automatically scan your home folder and apply the covers immediately. 

If you ever add new games or want to uninstall, you can open **Cascabel Covers** from your application menu.
