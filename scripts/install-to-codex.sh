#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CODEX_HOME="${CODEX_HOME:-/Volumes/ssd/work/.codex}"

mkdir -p "${CODEX_HOME}/bin" "${CODEX_HOME}/skills"

rsync -a "${REPO_ROOT}/bin/" "${CODEX_HOME}/bin/"
rsync -a --delete "${REPO_ROOT}/skills/voice-stack/" "${CODEX_HOME}/skills/voice-stack/"

chmod +x \
  "${CODEX_HOME}/bin/voice-asr" \
  "${CODEX_HOME}/bin/voice-asr-up" \
  "${CODEX_HOME}/bin/voice-asr-down" \
  "${CODEX_HOME}/bin/voice-asr-logs" \
  "${CODEX_HOME}/bin/codex_kokoro_tts.py" \
  "${CODEX_HOME}/bin/index-tts2-service.py" \
  "${CODEX_HOME}/bin/index-tts2-up" \
  "${CODEX_HOME}/bin/index-tts2-down" \
  "${CODEX_HOME}/bin/index-tts2-logs" \
  "${CODEX_HOME}/bin/index-tts2-say" \
  "${CODEX_HOME}/bin/codex-pet-say" \
  "${CODEX_HOME}/bin/codex-qq-notify-voice" \
  "${CODEX_HOME}/skills/voice-stack/scripts/check-voice-stack.sh"

echo "Installed Codex voice stack source into ${CODEX_HOME}"

