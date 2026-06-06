# Dependencies

Default locations are portable: `CODEX_HOME` defaults to `$HOME/.codex` and
`CODEX_SERVER_ROOT` defaults to `$HOME/.codex/servers`.

## Runtime

- Python 3.10+.
- Docker Compose for the ASR service wrappers.
- `curl`, `jq` optional for prettier ASR output, and standard Unix shell tools for macOS/Linux/WSL wrappers.
- PowerShell 5+ or PowerShell 7+ for Windows installation.
- macOS `afconvert` for QQ voice conversion and `afplay` for local playback.
- Node.js only indirectly through the desktop pet project if `codex-pet-say` is used.
- Python 3.11+ for the optional RealtimeSTT microphone listener runtime.

Docker is not required to install this plugin. It is only needed when the chosen
ASR or TTS runtime is deployed through Docker Compose.

## Kokoro TTS

`codex_kokoro_tts.py` imports:

- `kokoro`
- `torch`
- `numpy`
- `soundfile`

It uses the model repo `hexgrad/Kokoro-82M-v1.1-zh` and writes WAV at 24000 Hz.

## IndexTTS2

`index-tts2-service.py` imports the external IndexTTS2 project dynamically:

- `indextts.infer_v2.IndexTTS2`

The model files are expected under `INDEX_TTS2_MODEL_DIR`, defaulting to
`${CODEX_SERVER_ROOT:-$HOME/.codex/servers}/voice-tts/models/IndexTeam/IndexTTS-2`.

The wrapper can use PyTorch options exposed by IndexTTS2:

- `--device`
- `--fp16`
- `--deepspeed`
- `--cuda-kernel`
- `--accel`
- `--torch-compile`

## ASR

`voice-asr` talks to an OpenAI-compatible `/v1/audio/transcriptions` endpoint.
The service itself is compose-managed outside this repo under
`${VOICE_ASR_HOME:-${CODEX_SERVER_ROOT:-$HOME/.codex/servers}/voice-asr}`.

## RealtimeSTT Listener

`codex-voice-listener-setup` creates a service-owned virtual environment under
`${CODEX_VOICE_LISTENER_HOME:-${CODEX_SERVER_ROOT:-$HOME/.codex/servers}/codex-voice-listener}/.venv`
and installs:

- `RealtimeSTT[faster-whisper]`

RealtimeSTT requires Python 3.11+ and a working microphone backend. On macOS,
install PortAudio first when PyAudio cannot build:

```bash
brew install portaudio
```

The default transcription model is `base`, language `zh`, compute type `int8`.
Downloaded models, transcripts, logs, PID files, and state stay under
`CODEX_VOICE_LISTENER_HOME`.

## QQ Voice

`codex-qq-notify-voice` requires AstrBot OpenAPI with `im` and `file` scopes.
It converts input audio to mono 16-bit WAV at `CODEX_QQ_VOICE_SAMPLE_RATE`.
