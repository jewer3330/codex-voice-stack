param()

$CodexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME ".codex" }
$ServerRoot = if ($env:CODEX_SERVER_ROOT) { $env:CODEX_SERVER_ROOT } else { Join-Path $CodexHome "servers" }
$ListenerHome = if ($env:CODEX_VOICE_LISTENER_HOME) { $env:CODEX_VOICE_LISTENER_HOME } else { Join-Path $ServerRoot "codex-voice-listener" }
$PidFile = Join-Path $ListenerHome "listener.pid"
$StateFile = Join-Path $ListenerHome "data\state.json"

if (Test-Path $PidFile) {
  $pidText = (Get-Content -Raw $PidFile).Trim()
  if ($pidText -and (Get-Process -Id ([int]$pidText) -ErrorAction SilentlyContinue)) {
    Write-Host "running: $pidText"
  } else {
    Write-Host "stale pid: $pidText"
  }
} else {
  Write-Host "stopped"
}

if (Test-Path $StateFile) {
  Get-Content -Raw $StateFile
}
