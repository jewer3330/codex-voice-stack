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
- Added the reusable `voice-stack` skill and route check script.
- Made service roots configurable through `CODEX_SERVER_ROOT`, `VOICE_TTS_HOME`,
  `VOICE_ASR_HOME`, `CODEX_DESKTOP_PET_HOME`, and IndexTTS2 environment vars.

## Install

```bash
scripts/install-to-codex.sh
```

Runtime models, generated audio, samples, ASR service state, and logs stay under
`/Volumes/ssd/servers/voice-tts` and `/Volumes/ssd/servers/voice-asr`.

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

