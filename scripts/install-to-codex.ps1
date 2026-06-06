param(
  [string]$CodexHome = $(if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME ".codex" }),
  [string]$CodexServerRoot = $(if ($env:CODEX_SERVER_ROOT) { $env:CODEX_SERVER_ROOT } else { Join-Path (Join-Path $HOME ".codex") "servers" }),
  [string]$MarketplaceFile = $(if ($env:CODEX_MARKETPLACE_FILE) { $env:CODEX_MARKETPLACE_FILE } else { Join-Path (Join-Path $CodexHome ".agents") "plugins\marketplace.json" })
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$BinDir = Join-Path $CodexHome "bin"
$SkillsDir = Join-Path $CodexHome "skills"
$PluginRoot = Join-Path $CodexHome "plugins"
$CodexPluginDir = Join-Path $PluginRoot "codex-voice-stack"

New-Item -ItemType Directory -Force -Path $BinDir, $SkillsDir, $PluginRoot, (Split-Path -Parent $MarketplaceFile) | Out-Null

Copy-Item -Recurse -Force (Join-Path $RepoRoot "bin\*") $BinDir

$SkillDest = Join-Path $SkillsDir "voice-stack"
if (Test-Path $SkillDest) { Remove-Item -Recurse -Force $SkillDest }
Copy-Item -Recurse -Force (Join-Path $RepoRoot "skills\voice-stack") $SkillDest

if (Test-Path $CodexPluginDir) { Remove-Item -Recurse -Force $CodexPluginDir }
New-Item -ItemType Directory -Force -Path $CodexPluginDir | Out-Null
Get-ChildItem -Force $RepoRoot | Where-Object {
  $_.Name -notin @(".git", ".codegraph", "__pycache__")
} | ForEach-Object {
  Copy-Item -Recurse -Force $_.FullName (Join-Path $CodexPluginDir $_.Name)
}

if (Test-Path $MarketplaceFile) {
  $marketplace = Get-Content -Raw -Path $MarketplaceFile | ConvertFrom-Json
} else {
  $marketplace = [pscustomobject]@{
    name = "personal"
    interface = [pscustomobject]@{ displayName = "Personal" }
    plugins = @()
  }
}

$entry = [pscustomobject]@{
  name = "codex-voice-stack"
  source = [pscustomobject]@{ source = "local"; path = "./plugins/codex-voice-stack" }
  policy = [pscustomobject]@{ installation = "AVAILABLE"; authentication = "ON_INSTALL" }
  category = "Productivity"
}
$plugins = @($marketplace.plugins)
$updated = $false
for ($i = 0; $i -lt $plugins.Count; $i++) {
  if ($plugins[$i].name -eq $entry.name) {
    $plugins[$i] = $entry
    $updated = $true
    break
  }
}
if (-not $updated) {
  $plugins += $entry
}
$marketplace.plugins = @($plugins)
$marketplace | ConvertTo-Json -Depth 10 | Set-Content -Encoding UTF8 -Path $MarketplaceFile

Write-Host "Installed Codex voice stack source into $CodexHome"
Write-Host "Registered Codex Voice Stack in $MarketplaceFile"
