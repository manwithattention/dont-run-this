---
slug: spyware-telegram-remote
status: approved
intent: clear
review_required: false
pending-action: write .omo/plans/spyware-telegram-remote.md
approach: Rewrite file_spyware.py sebagai Telegram bot controller yang jalankan semua 7 modul SpyWare (audio, clipboard, domains, files, key, screen, webcam) via command handler. Modul berjalan di background thread. Bot kirim output file ke Telegram. Compile ke .exe pakai PyInstaller. Deploy ke Windows VM.
---

# Draft: spyware-telegram-remote

## Components (topology ledger)

| ID | Outcome | Status | Evidence |
|----|---------|--------|----------|
| C1 | Bot controller: `file_spyware.py` rewrite dengan 7 command handlers + `/start`, `/status`, `/stop`, `/help` | active | SpyWare/SpyWare.py (spy function pattern) |
| C2 | Background spy runner: semua modul jalan di daemon thread, bisa start/stop per modul | active | SpyWare.spy() threading pattern |
| C3 | Compilation: PyInstaller → single .exe | active | SpyWare_onefile.spec |
| C4 | Deployment guide: autostart di Windows VM | active | SpyWare.enabled() function |

## Open assumptions (announced defaults)

| Assumption | Default | Rationale | Reversible? |
|-----------|---------|-----------|-------------|
| Token storage | .env file, baca via `os.environ` | Hardcode token expose risk | Yes |
| Polling vs webhook | `infinity_polling()` | Simpler, no public IP needed | Yes |
| File cleanup | Keep all locally | Simplest | Yes |
| Config files | Pakai default SpyWare configs | Library sudah punya defaults | Yes |

## Findings (cited - path:lines)

- `SpyWare/SpyWare.py`: `spy()` function starts each module in Thread with `daemon=True`, uses `config_load()` per module then `Daemon().run_for_ever()` — exception: domains module uses `run_CacheDns()` + `run_AppData()`
- Each module exports: `Daemon`, `config_load`, `CONFIGURATIONS`
- Module names: audio, clipboard, domains, files, key, screen, webcam
- Output files per default config: `keySpy.txt`, `clipboard.txt`, `domains.txt`, `files.csv`, `screenshots/*.png`, `pictures/*.png`, `records/*.wav`
- `comunicate.py`: existing Telegram sender pattern using `requests.post` to Telegram API

## Decisions (with rationale)

1. **Semua 7 modul** punya command handler: `/screenshot`, `/keylog`, `/clipboard`, `/webcam`, `/audio`, `/files`, `/domains`
2. **Background mode**: `/startall` jalankan semua modul di background threads (seperti `spy()` asli), `/stopall` stop semua
3. **On-demand mode**: tiap command (misal `/screenshot`) trigger modul sekali, ambil output, kirim ke Telegram
4. **Utility commands**: `/start` (help), `/status` (running modules), `/help` (command list)
5. Token dari `.env` file atau environment variable

## Scope IN

- Rewrite `file_spyware.py` — full Telegram bot controller
- 7 command handlers (1 per SpyWare module)
- Start/stop all modules background
- Send output files (photo, document, text) back to Telegram
- `.env` file for token
- PyInstaller compile command
- Autostart setup guide

## Scope OUT (Must NOT have)

- Webhook mode (butuh public IP)
- Custom SpyWare module modifications (use as-is from pip)
- Encryption/obfuscation
- Multi-user bot (single CHAT_ID only)
- Web dashboard

## Open questions

None — all defaults adopted, user approved approach.

## Approval gate
status: approved
