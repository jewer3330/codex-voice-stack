#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CODEX_HOME="${CODEX_HOME:-${HOME}/.codex}"
CODEX_SERVER_ROOT="${CODEX_SERVER_ROOT:-${HOME}/.codex/servers}"
CODEX_PLUGIN_DIR="${CODEX_HOME}/plugins/codex-voice-stack"
MARKETPLACE_FILE="${CODEX_MARKETPLACE_FILE:-${CODEX_HOME}/.agents/plugins/marketplace.json}"

mkdir -p "${CODEX_HOME}/bin" "${CODEX_HOME}/skills" "${CODEX_HOME}/plugins"
mkdir -p "$(dirname "$MARKETPLACE_FILE")"

rsync -a "${REPO_ROOT}/bin/" "${CODEX_HOME}/bin/"
rsync -a --delete "${REPO_ROOT}/skills/voice-stack/" "${CODEX_HOME}/skills/voice-stack/"
rsync -a --delete \
  --exclude '.git/' \
  --exclude '.codegraph/' \
  --exclude '__pycache__/' \
  "${REPO_ROOT}/" "${CODEX_PLUGIN_DIR}/"

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

python3 - "$MARKETPLACE_FILE" <<'PY'
import json
import sys
from pathlib import Path

marketplace = Path(sys.argv[1])
entry = {
    "name": "codex-voice-stack",
    "source": {"source": "local", "path": "./plugins/codex-voice-stack"},
    "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
    "category": "Productivity",
}
if marketplace.exists():
    data = json.loads(marketplace.read_text(encoding="utf-8"))
else:
    data = {"name": "personal", "interface": {"displayName": "Personal"}, "plugins": []}
plugins = data.setdefault("plugins", [])
for index, plugin in enumerate(plugins):
    if plugin.get("name") == entry["name"]:
        plugins[index] = entry
        break
else:
    plugins.append(entry)
marketplace.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY

echo "Installed Codex voice stack source into ${CODEX_HOME}"
echo "Registered Codex Voice Stack in ${MARKETPLACE_FILE}"
