param(
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$Args
)

$ErrorActionPreference = "Stop"
$CodexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME ".codex" }
$ServerRoot = if ($env:CODEX_SERVER_ROOT) { $env:CODEX_SERVER_ROOT } else { Join-Path $CodexHome "servers" }
$ListenerHome = if ($env:CODEX_VOICE_LISTENER_HOME) { $env:CODEX_VOICE_LISTENER_HOME } else { Join-Path $ServerRoot "codex-voice-listener" }
$PythonBin = if ($env:CODEX_VOICE_LISTENER_PYTHON_BIN) { $env:CODEX_VOICE_LISTENER_PYTHON_BIN } else { Join-Path $ListenerHome ".venv\Scripts\python.exe" }
$Script = Join-Path $PSScriptRoot "codex_realtimestt_listener.py"

if (-not (Test-Path $PythonBin)) {
  throw "Runtime not found at $PythonBin. Run codex-voice-listener-setup.ps1 first."
}

& $PythonBin $Script listen-once @Args
