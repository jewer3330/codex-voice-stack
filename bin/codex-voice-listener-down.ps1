param()

$ErrorActionPreference = "Stop"
$CodexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME ".codex" }
$ServerRoot = if ($env:CODEX_SERVER_ROOT) { $env:CODEX_SERVER_ROOT } else { Join-Path $CodexHome "servers" }
$ListenerHome = if ($env:CODEX_VOICE_LISTENER_HOME) { $env:CODEX_VOICE_LISTENER_HOME } else { Join-Path $ServerRoot "codex-voice-listener" }
$PidFile = Join-Path $ListenerHome "listener.pid"

if (-not (Test-Path $PidFile)) {
  Write-Host "codex voice listener is not running"
  exit 0
}

$pidText = (Get-Content -Raw $PidFile).Trim()
if (-not $pidText) {
  Remove-Item -Force $PidFile
  Write-Host "codex voice listener is not running"
  exit 0
}

$proc = Get-Process -Id ([int]$pidText) -ErrorAction SilentlyContinue
if (-not $proc) {
  Remove-Item -Force $PidFile
  Write-Host "codex voice listener is not running"
  exit 0
}

Stop-Process -Id $proc.Id -Force
Remove-Item -Force $PidFile
Write-Host "codex voice listener stopped"
