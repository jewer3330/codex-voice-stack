---
name: voice-stack
description: Use when setting up, operating, packaging, or troubleshooting Codex voice capabilities. Covers text-to-speech, speech-to-text, wake/listen routing, desktop pet speech, QQ voice replies, Kokoro, IndexTTS2, voice-ASR service wrappers, storage layout, model/output boundaries, and reusable voice tooling in the local Codex extensions repository.
---

# Voice Stack

Use this skill when the user asks Codex to speak, listen, transcribe audio, send a voice reply to QQ, choose or package voice models, or wire voice into the desktop pet.

## Route Choice

- Desktop pet speech: `${CODEX_HOME:-$HOME/.codex}/bin/codex-pet-say "text"`.
- Unified Codex status with speech: `${CODEX_HOME:-$HOME/.codex}/bin/codex-self --say <phase> <summary>`.
- QQ voice message from an existing wav: `${CODEX_HOME:-$HOME/.codex}/bin/codex-qq-notify-voice /path/file.wav "text"`.
- Open-source local TTS draft: `${CODEX_HOME:-$HOME/.codex}/bin/codex_kokoro_tts.py`.
- Warm mature TTS service: `index-tts2-up`, then `index-tts2-say "text"`.
- Speech-to-text: `voice-asr FILE` after `voice-asr-up`.

Read `references/voice-routes.md` for paths, service contracts, and packaging details.

## TTS

Kokoro one-shot local generation:

```bash
${CODEX_HOME:-$HOME/.codex}/bin/codex_kokoro_tts.py --text-file text.txt --out ${VOICE_TTS_HOME:-${CODEX_SERVER_ROOT:-$HOME/.codex/servers}/voice-tts}/outputs/kokoro.wav --voice zf_017
```

IndexTTS2 warmed service:

```bash
${CODEX_HOME:-$HOME/.codex}/bin/index-tts2-up
${CODEX_HOME:-$HOME/.codex}/bin/index-tts2-say "你好，我是小莫。"
```

Send a wav to QQ:

```bash
${CODEX_HOME:-$HOME/.codex}/bin/codex-qq-notify-voice /absolute/path/reply.wav "语音回复"
```

## ASR

Start the ASR service and transcribe:

```bash
${CODEX_HOME:-$HOME/.codex}/bin/voice-asr-up
${CODEX_HOME:-$HOME/.codex}/bin/voice-asr /absolute/path/input.wav
```

Use `--raw` for raw JSON and `--language auto` when language is unknown.

## Desktop Pet

Use the desktop pet route when the user expects Codex's visible avatar to speak:

```bash
${CODEX_HOME:-$HOME/.codex}/bin/codex-pet-say "这句话会通过桌宠说出来"
```

Wake/listen wrappers live beside it: `codex-pet-wake-up`, `codex-pet-wake-down`, `codex-pet-wake-command`, and `codex-pet-wake-listen`.

## Storage Rules

- Keep wrappers, service scripts, and skills under `${CODEX_HOME:-$HOME/.codex}`.
- Keep voice services, models, prompts, generated wavs, and logs under `${CODEX_SERVER_ROOT:-$HOME/.codex/servers}/voice-tts` or `${CODEX_SERVER_ROOT:-$HOME/.codex/servers}/voice-asr`.
- Keep desktop pet source under `${CODEX_DESKTOP_PET_HOME:-$HOME/codex-desktop-pet}`; persistent pet data can live under `${CODEX_SERVER_ROOT:-$HOME/.codex/servers}/codex-desktop-pet`.
- Do not commit model checkpoints, generated audio, virtualenvs, voice samples, QQ attachments, or API keys.

## Checks

Run:

```bash
${CODEX_HOME:-$HOME/.codex}/skills/voice-stack/scripts/check-voice-stack.sh
```

Then run syntax checks on edited wrappers and scan tracked files for secrets before committing.
