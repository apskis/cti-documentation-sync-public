<#
.SYNOPSIS
  Toggle Claude Code between enterprise Claude (SSO) and AWS Bedrock.

.DESCRIPTION
  Swaps the env block in .claude/settings.json between two modes:
    - enterprise:  empty env block, uses your SSO login and latest models
    - bedrock:     CLAUDE_CODE_USE_BEDROCK=1, AWS region, Opus/Haiku pins

  Also updates .env to comment/uncomment the Bedrock routing lines.

  Claude Code reads settings.json at startup, so restart your session
  after toggling.

.EXAMPLE
  .\switch_provider.ps1              # show current mode
  .\switch_provider.ps1 enterprise   # switch to enterprise Claude
  .\switch_provider.ps1 bedrock      # switch to AWS Bedrock
#>
param(
    [ValidateSet("enterprise", "bedrock", "status")]
    [string]$Mode = "status"
)

$ErrorActionPreference = "Stop"
$repo = (Get-Location).Path
$settingsPath = "$repo\.claude\settings.json"
$envPath = "$repo\.env"

if (-not (Test-Path $settingsPath)) {
    Write-Host "ERROR: $settingsPath not found. Run from the repo root." -ForegroundColor Red
    exit 1
}

$raw = Get-Content $settingsPath -Raw -Encoding UTF8
$isBedrock = $raw -match '"CLAUDE_CODE_USE_BEDROCK"\s*:\s*"1"'

$current = if ($isBedrock) { "bedrock" } else { "enterprise" }

if ($Mode -eq "status") {
    Write-Host ""
    Write-Host "Current provider: " -NoNewline
    if ($current -eq "enterprise") {
        Write-Host "ENTERPRISE (SSO)" -ForegroundColor Green
        Write-Host "  Using your enterprise Claude account. Latest models via SSO."
    } else {
        Write-Host "AWS BEDROCK" -ForegroundColor Cyan
        Write-Host "  Traffic stays in the GeneLabs AWS account."
    }
    Write-Host ""
    Write-Host "Usage:  .\switch_provider.ps1 enterprise"
    Write-Host "        .\switch_provider.ps1 bedrock"
    Write-Host ""
    exit 0
}

if ($Mode -eq $current) {
    Write-Host "Already on $Mode - nothing to do." -ForegroundColor Yellow
    exit 0
}

# --- Enterprise env block (empty) ---
$envEnterprise = '  "env": {},'

# --- Bedrock env block ---
$envBedrock = @'
  "env": {
    "CLAUDE_CODE_USE_BEDROCK": "1",
    "AWS_REGION": "us-east-1",
    "ANTHROPIC_MODEL": "us.anthropic.claude-opus-5",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "us.anthropic.claude-haiku-4-5-20251001-v1:0"
  },
'@

$commentEnterprise = 'Non-secret project settings. Bedrock is OFF - using enterprise Claude account via SSO.'
$commentBedrock    = 'Non-secret project settings. Bedrock is ON - traffic stays in the GeneLabs AWS account.'
$noteEnterprise    = 'Using enterprise Claude account via SSO. Latest models available. Switch: .\switch_provider.ps1 bedrock'
$noteBedrock       = 'Opus primary, Haiku for background. WebSearch unavailable. Switch: .\switch_provider.ps1 enterprise'

if ($Mode -eq "enterprise") {
    $raw = $raw -replace '(?ms)"env"\s*:\s*\{[^}]*\}\s*,', $envEnterprise
    $raw = $raw -replace '(?<="_comment":\s*").*?(?=")', $commentEnterprise
    $raw = $raw -replace '(?<="_model_note":\s*").*?(?=")', $noteEnterprise

    Write-Host ""
    Write-Host "Switched to: ENTERPRISE (SSO)" -ForegroundColor Green
    Write-Host "  Claude Code will use your enterprise account and latest models."
    Write-Host "  WebSearch is available." -ForegroundColor DarkGray
}

if ($Mode -eq "bedrock") {
    $raw = $raw -replace '(?ms)"env"\s*:\s*\{[^}]*\}\s*,', $envBedrock
    $raw = $raw -replace '(?<="_comment":\s*").*?(?=")', $commentBedrock
    $raw = $raw -replace '(?<="_model_note":\s*").*?(?=")', $noteBedrock

    Write-Host ""
    Write-Host "Switched to: AWS BEDROCK" -ForegroundColor Cyan
    Write-Host "  Region:  us-east-1"
    Write-Host "  Primary: us.anthropic.claude-opus-5"
    Write-Host "  Haiku:   us.anthropic.claude-haiku-4-5-20251001-v1:0"
    Write-Host "  WebSearch is NOT available - use search MCP or feed-only." -ForegroundColor Yellow
    Write-Host "  AWS credentials required." -ForegroundColor Yellow

    # Check for an active AWS session
    try {
        $null = aws sts get-caller-identity 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  AWS session: active" -ForegroundColor Green
        } else { throw }
    } catch {
        Write-Host ""
        Write-Host "  No active AWS session. Authenticate first:" -ForegroundColor Red
        Write-Host "    .\scripts\aws_login.ps1 -Login" -ForegroundColor Yellow
    }
}

[System.IO.File]::WriteAllText($settingsPath, $raw, [System.Text.UTF8Encoding]::new($false))

if (Test-Path $envPath) {
    $envLines = Get-Content $envPath
    $out = @()
    $bedrockKeys = @("CLAUDE_CODE_USE_BEDROCK", "AWS_REGION", "ANTHROPIC_MODEL", "ANTHROPIC_DEFAULT_HAIKU_MODEL")
    foreach ($line in $envLines) {
        if ($Mode -eq "enterprise") {
            foreach ($k in $bedrockKeys) {
                if ($line -match "^${k}=") { $line = "#$line"; break }
            }
        }
        if ($Mode -eq "bedrock") {
            foreach ($k in $bedrockKeys) {
                if ($line -match "^#${k}=") { $line = $line.Substring(1); break }
            }
        }
        $out += $line
    }
    Set-Content -Path $envPath -Value $out -Encoding UTF8
}

Write-Host ""
Write-Host "Restart your Claude Code session for the change to take effect." -ForegroundColor DarkGray
Write-Host ""
