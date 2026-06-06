#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CODEX_HOME="${CODEX_HOME:-$(cd "${SCRIPT_DIR}/../../.." && pwd)}"
SERVER_ROOT="${CODEX_SERVER_ROOT:-${HOME}/.codex/servers}"
VOICE_TTS_HOME="${VOICE_TTS_HOME:-${SERVER_ROOT}/voice-tts}"

required=(
  "$CODEX_HOME/bin/codex-pet-say"
  "$CODEX_HOME/bin/codex_kokoro_tts.py"
  "$CODEX_HOME/bin/codex-qq-notify-voice"
  "$CODEX_HOME/bin/voice-asr"
  "$CODEX_HOME/bin/voice-asr-up"
  "$CODEX_HOME/bin/index-tts2-service.py"
  "$CODEX_HOME/bin/index-tts2-up"
  "$CODEX_HOME/bin/index-tts2-say"
)

for path in "${required[@]}"; do
  if [[ ! -x "$path" ]]; then
    echo "missing executable: $path" >&2
    exit 1
  fi
done

mkdir -p "$VOICE_TTS_HOME/outputs/index-tts2" "$VOICE_TTS_HOME/logs"
"$CODEX_HOME/bin/index-tts2-service.py" --help >/dev/null
"$CODEX_HOME/bin/voice-asr" --help >/dev/null

if curl -fsS "${VOICE_ASR_BASE_URL:-http://127.0.0.1:19135}/health" >/dev/null 2>&1; then
  echo "voice ASR: healthy"
else
  echo "voice ASR: not running"
fi

if curl -fsS "http://${INDEX_TTS2_HOST:-127.0.0.1}:${INDEX_TTS2_PORT:-49231}/health" >/dev/null 2>&1; then
  echo "IndexTTS2: healthy"
else
  echo "IndexTTS2: not running"
fi

echo "voice stack ok"
