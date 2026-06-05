# Voice Route Reference

## Storage

```text
CODEX_HOME=/Volumes/ssd/work/.codex
CODEX_SERVER_ROOT=/Volumes/ssd/servers
VOICE_TTS_HOME=/Volumes/ssd/servers/voice-tts
VOICE_ASR_HOME=/Volumes/ssd/servers/voice-asr
CODEX_DESKTOP_PET_HOME=/Volumes/ssd/work/codex-desktop-pet
INDEX_TTS_REPO=/Volumes/ssd/work/.codex/bin/index-tts
INDEX_TTS2_MODEL_DIR=/Volumes/ssd/servers/voice-tts/models/IndexTeam/IndexTTS-2
INDEX_TTS2_OUTPUT_DIR=/Volumes/ssd/servers/voice-tts/outputs/index-tts2
```

Repository files contain wrappers and small bridge scripts only. Runtime data stays under `servers`.

## Text To Speech

### Desktop Pet

`codex-pet-say` changes into `CODEX_DESKTOP_PET_HOME` and runs `scripts/say.js`. Use this when the user expects the on-screen Codex avatar to talk.

### Kokoro

`codex_kokoro_tts.py` is a one-shot generator. It uses `hexgrad/Kokoro-82M-v1.1-zh` through the local Python environment where Kokoro is installed. Choose this for open-source local neural TTS drafts and voice comparisons.

### IndexTTS2

`index-tts2-service.py` keeps IndexTTS2 warm behind localhost HTTP:

- `GET /health`
- `POST /synthesize` with JSON body `{ "text": "...", "output_path": "optional.wav" }`

Wrappers:

```bash
index-tts2-up
index-tts2-say "text"
index-tts2-logs
index-tts2-down
```

IndexTTS2 repo and model files are not committed. They must exist at `INDEX_TTS_REPO` and `INDEX_TTS2_MODEL_DIR`.

## Speech To Text

The ASR service is compose-managed under `VOICE_ASR_HOME`:

```bash
voice-asr-up
voice-asr /path/audio.wav
voice-asr --health
voice-asr-logs
voice-asr-down
```

`voice-asr` calls an OpenAI-compatible `/v1/audio/transcriptions` endpoint. Use `VOICE_ASR_BASE_URL`, `VOICE_ASR_API_KEY`, `VOICE_ASR_MODEL`, and `VOICE_ASR_LANGUAGE` to override defaults.

## QQ Voice

`codex-qq-notify-voice` uploads a local audio file to AstrBot OpenAPI and sends it as a QQ voice record. It converts audio through `afconvert` to mono 16-bit WAV at `CODEX_QQ_VOICE_SAMPLE_RATE`.

Required:

```text
ASTRBOT_URL=http://127.0.0.1:6185
ASTRBOT_OPENAPI_KEY_FILE=/Volumes/ssd/servers/astrbot/data/codex_openapi_im.key
CODEX_QQ_NOTIFY_UMO=<AstrBot unified message origin>
```

The OpenAPI key needs `im` and `file` scopes.

## Commit Checklist

- [ ] No generated wav/mp3/m4a files staged.
- [ ] No model directories, virtualenvs, or checkpoints staged.
- [ ] `index-tts2-service.py --help` works.
- [ ] `voice-asr --help` works.
- [ ] `codex-pet-say` remains configurable with `CODEX_DESKTOP_PET_HOME`.
- [ ] Secret scan finds no API keys, QQ tokens, or GitHub tokens in tracked files.
