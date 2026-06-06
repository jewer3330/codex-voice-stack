# Change Log

## 0.1.0

- Split voice capabilities into a standalone development source project.
- Packaged ASR CLI wrappers, Kokoro TTS, IndexTTS2 warmed service wrappers,
  desktop pet speech routing, QQ voice notification, and the `voice-stack` skill.
- Documented libraries, external model boundaries, and generated-audio storage.
- Added install and check scripts so this source tree can promote its files into
  a local `.codex` installation.
- Made install docs and wrapper defaults portable by using `$HOME/.codex` and
  `$HOME/.codex/servers` unless overridden by environment variables.
- Added a PowerShell installer for Windows file installation.
- Installers now copy the full plugin source into `.codex/plugins/codex-voice-stack`
  and register it in the personal Codex marketplace.
