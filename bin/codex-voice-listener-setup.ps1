param(
  [string]$Python = $(if ($env:CODEX_VOICE_LISTENER_PYTHON) { $env:CODEX_VOICE_LISTENER_PYTHON } else { "python" }),
  [switch]$Recreate,
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$Args
)

$ErrorActionPreference = "Stop"
$Script = Join-Path $PSScriptRoot "codex_realtimestt_listener.py"
$setupArgs = @("setup", "--python", $Python)
if ($Recreate) { $setupArgs += "--recreate" }
$setupArgs += $Args
& $Python $Script @setupArgs
