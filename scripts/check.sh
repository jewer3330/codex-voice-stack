#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

zsh -n \
  "${REPO_ROOT}/bin/voice-asr" \
  "${REPO_ROOT}/bin/voice-asr-up" \
  "${REPO_ROOT}/bin/voice-asr-down" \
  "${REPO_ROOT}/bin/voice-asr-logs" \
  "${REPO_ROOT}/bin/index-tts2-up" \
  "${REPO_ROOT}/bin/index-tts2-down" \
  "${REPO_ROOT}/bin/index-tts2-logs" \
  "${REPO_ROOT}/bin/index-tts2-say" \
  "${REPO_ROOT}/bin/codex-pet-say" \
  "${REPO_ROOT}/bin/codex-qq-notify-voice" \
  "${REPO_ROOT}/scripts/install-to-codex.sh" \
  "${REPO_ROOT}/skills/voice-stack/scripts/check-voice-stack.sh"

python3 -m py_compile \
  "${REPO_ROOT}/bin/codex_kokoro_tts.py" \
  "${REPO_ROOT}/bin/index-tts2-service.py"

"${REPO_ROOT}/bin/index-tts2-service.py" --help >/dev/null
"${REPO_ROOT}/bin/voice-asr" --help >/dev/null

echo "codex-voice-stack checks ok"

