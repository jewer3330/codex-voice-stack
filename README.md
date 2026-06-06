# Codex Voice Stack

This is the development source project for Codex voice capabilities. It keeps
editable source separate from installed `.codex/bin` wrappers and the installed
`.codex/skills/voice-stack` skill.

## What Changed

- Added `voice-asr` and compose wrappers for a local OpenAI-compatible speech
  transcription service.
- Added `codex_kokoro_tts.py` for one-shot local Kokoro speech generation.
- Added `index-tts2-service.py` and wrappers for a warmed IndexTTS2 HTTP service.
- Added `codex-pet-say` for desktop Live2D pet speech routing.
- Added `codex-qq-notify-voice` for QQ voice message delivery through AstrBot.
- Added RealtimeSTT microphone wrappers for `小莫小莫 -> Codex -> local speech`
  flows while keeping the listener as an explicitly started/stopped process.
- Added the reusable `voice-stack` skill and route check script.
- Made service roots configurable through `CODEX_SERVER_ROOT`, `VOICE_TTS_HOME`,
  `VOICE_ASR_HOME`, `CODEX_DESKTOP_PET_HOME`, and IndexTTS2 environment vars.

## Install

macOS/Linux/WSL/Git Bash:

```bash
scripts/install-to-codex.sh
```

Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/install-to-codex.ps1
```

The install script is lightweight: it copies source-controlled wrappers, skills,
plugin source, and marketplace metadata. It does not require Docker, download
models, install voice engines, or create service runtime data by default.

When you enable local voice services, runtime models, generated audio, samples,
ASR service state, and logs stay under
`${CODEX_SERVER_ROOT:-$HOME/.codex/servers}/voice-tts` and
`${CODEX_SERVER_ROOT:-$HOME/.codex/servers}/voice-asr`, or the corresponding
environment-variable overrides.

For local microphone wake/listen, run setup only when needed:

```bash
codex-voice-listener-setup
codex-listen-once
codex-voice-listener-up --dispatch codex --reply "{reply}"
codex-voice-listener-status
codex-voice-listener-down
```

The RealtimeSTT runtime venv, model cache, logs, PID files, and transcripts stay
under `${CODEX_VOICE_LISTENER_HOME:-${CODEX_SERVER_ROOT:-$HOME/.codex/servers}/codex-voice-listener}`.

Use environment variables to install into a different Codex home or service
root:

```bash
CODEX_HOME=/path/to/.codex CODEX_SERVER_ROOT=/path/to/servers scripts/install-to-codex.sh
```

The installer copies source-controlled files into `.codex/bin`,
`.codex/skills/voice-stack`, `.codex/plugins/codex-voice-stack`, and the
personal marketplace file.

## Marketplace

Install scripts register this plugin in the personal Codex marketplace at
`${CODEX_MARKETPLACE_FILE:-$CODEX_HOME/.agents/plugins/marketplace.json}` with
source path `./plugins/codex-voice-stack`.

## Windows Notes

Windows installation is supported. Runtime support is mixed: Python helpers can
run on Windows when their Python libraries are installed, while shell service
wrappers, `afplay`, and QQ voice conversion via `afconvert` require macOS,
Linux, or WSL/Git Bash today. Docker is optional and only needed for a chosen
ASR/TTS service deployment that uses Docker. A future ffmpeg route should
replace the macOS audio conversion dependency.

## Check

```bash
scripts/check.sh
```

The check validates shell syntax, Python syntax, and command help paths. It does
not download models.

## Runtime Data Boundary

Do not commit voice models, prompt samples, generated audio, QQ attachments,
virtualenvs, service logs, API keys, or tokens. Commit only wrappers, small
service code, skills, documentation, and installer logic.
