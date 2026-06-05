# Dependencies

## Runtime

- Python 3.10+.
- Docker Compose for the ASR service wrappers.
- `curl`, `jq` optional for prettier ASR output, and standard Unix shell tools.
- macOS `afconvert` for QQ voice conversion and `afplay` for local playback.
- Node.js only indirectly through the desktop pet project if `codex-pet-say` is used.

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
`/Volumes/ssd/servers/voice-tts/models/IndexTeam/IndexTTS-2`.

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
`/Volumes/ssd/servers/voice-asr`.

## QQ Voice

`codex-qq-notify-voice` requires AstrBot OpenAPI with `im` and `file` scopes.
It converts input audio to mono 16-bit WAV at `CODEX_QQ_VOICE_SAMPLE_RATE`.

