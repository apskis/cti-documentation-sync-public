<#
.SYNOPSIS
  Load config\bedrock.env into the current PowerShell session.

.DESCRIPTION
  Dot-source it so the variables survive:

      . .\scripts\load_bedrock_env.ps1

  Existing variables are not overwritten, so an SSO session you already have
  beats the file.

  To make the settings permanent instead, use Claude Code's own wizard: run
  `claude`, choose 3rd-party platform, then Amazon Bedrock. It writes
  ~\.claude\settings.json and you never touch environment variables.
#>

$repo = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $repo "config\bedrock.env"

if (-not (Test-Path $envFile)) {
    Write-Warning "config\bedrock.env not found. Copy config\bedrock.env.example to it."
    return
}

$loaded = 0
Get-Content $envFile | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith("#") -or ($line -notmatch "=")) { return }
    $key, $value = $line -split "=", 2
    $key = $key.Trim()
    $value = $value.Trim().Trim('"').Trim("'")
    if (-not $value) { return }
    if (-not [Environment]::GetEnvironmentVariable($key)) {
        Set-Item -Path "env:$key" -Value $value
        $script:loaded++
    }
}

Write-Host "Loaded $loaded variable(s) from config\bedrock.env"
Write-Host "  CLAUDE_CODE_USE_BEDROCK=$($env:CLAUDE_CODE_USE_BEDROCK)"
Write-Host "  AWS_REGION=$($env:AWS_REGION)"
Write-Host "  ANTHROPIC_MODEL=$($env:ANTHROPIC_MODEL)"
