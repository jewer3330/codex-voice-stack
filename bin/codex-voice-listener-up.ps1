param(
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$Args
)

$ErrorActionPreference = "Stop"
$CodexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME ".codex" }
$ServerRoot = if ($env:CODEX_SERVER_ROOT) { $env:CODEX_SERVER_ROOT } else { Join-Path $CodexHome "servers" }
$ListenerHome = if ($env:CODEX_VOICE_LISTENER_HOME) { $env:CODEX_VOICE_LISTENER_HOME } else { Join-Path $ServerRoot "codex-voice-listener" }
$LogDir = Join-Path $ListenerHome "logs"
$DataDir = Join-Path $ListenerHome "data"
$PidFile = Join-Path $ListenerHome "listener.pid"
$PythonBin = if ($env:CODEX_VOICE_LISTENER_PYTHON_BIN) { $env:CODEX_VOICE_LISTENER_PYTHON_BIN } else { Join-Path $ListenerHome ".venv\Scripts\python.exe" }
$Script = Join-Path $PSScriptRoot "codex_realtimestt_listener.py"

New-Item -ItemType Directory -Force -Path $LogDir, $DataDir | Out-Null

if (Test-Path $PidFile) {
  $oldPid = Get-Content -Raw $PidFile
  $oldPid = $oldPid.Trim()
  if ($oldPid -and (Get-Process -Id ([int]$oldPid) -ErrorAction SilentlyContinue)) {
    Write-Host "codex voice listener already running: $oldPid"
    exit 0
  }
}

if (-not (Test-Path $PythonBin)) {
  throw "Runtime not found at $PythonBin. Run codex-voice-listener-setup.ps1 first."
}

$stdout = Join-Path $LogDir "listener.log"
$stderr = Join-Path $LogDir "listener.err.log"
$proc = Start-Process -FilePath $PythonBin -ArgumentList @($Script, "listen-loop") + $Args -NoNewWindow -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
Set-Content -Encoding ASCII -Path $PidFile -Value $proc.Id
Write-Host "codex voice listener started: $($proc.Id)"
