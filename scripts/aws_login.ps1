<#
.SYNOPSIS
  Authenticate to AWS for Bedrock and verify the session.

.DESCRIPTION
  Three credential paths, tried in order:

    1. Active session from `aws login` (Okta SAML via the browser).
       Lasts 1-12 hours depending on role config. This is the preferred
       path for interactive work.

    2. Environment variables (AWS_ACCESS_KEY_ID, etc.).
       Used by the headless runner when sourced from bedrock.env, or
       when pasting temporary CloudShell credentials.

    3. Named AWS profile (AWS_PROFILE).
       For SSO profiles: `aws sso login --profile <name>` first.

  Run with no arguments to check the current session. Pass -Login to
  open the browser and authenticate. Pass -Export to write short-lived
  env vars for tools that need them (like the Anthropic SDK).

.EXAMPLE
  .\scripts\aws_login.ps1               # check current session
  .\scripts\aws_login.ps1 -Login        # authenticate via browser
  .\scripts\aws_login.ps1 -Export       # export creds to env vars
  .\scripts\aws_login.ps1 -Login -Export # login then export
#>
param(
    [switch]$Login,
    [switch]$Export
)

$ErrorActionPreference = "Stop"

$expectedAccount = "<ACCOUNT_ID>"
$expectedRole    = "<your-cybersecurity-role>"
$region          = "us-east-1"

function Test-AwsSession {
    try {
        $id = aws sts get-caller-identity --output json 2>$null | ConvertFrom-Json
        if ($id.Account -eq $expectedAccount -and $id.Arn -match $expectedRole) {
            return $id
        }
        Write-Host "  Session active but wrong identity:" -ForegroundColor Yellow
        Write-Host "    Account: $($id.Account)  (expected $expectedAccount)"
        Write-Host "    Arn:     $($id.Arn)"
        return $null
    } catch {
        return $null
    }
}

# --- Login ---
if ($Login) {
    Write-Host ""
    Write-Host "Opening browser for AWS login..." -ForegroundColor Cyan
    aws login 2>&1 | Out-Host
    Write-Host ""
}

# --- Check ---
Write-Host ""
$id = Test-AwsSession
if ($id) {
    Write-Host "AWS session active" -ForegroundColor Green
    Write-Host "  Account:  $($id.Account)"
    Write-Host "  Role:     $expectedRole"
    Write-Host "  Region:   $region"
} else {
    Write-Host "No active AWS session for $expectedAccount / $expectedRole" -ForegroundColor Red
    Write-Host ""
    Write-Host "To authenticate:" -ForegroundColor Yellow
    Write-Host "  .\scripts\aws_login.ps1 -Login"
    Write-Host ""
    Write-Host "Or paste CloudShell credentials:" -ForegroundColor Yellow
    Write-Host '  $env:AWS_ACCESS_KEY_ID     = "..."'
    Write-Host '  $env:AWS_SECRET_ACCESS_KEY = "..."'
    Write-Host '  $env:AWS_SESSION_TOKEN     = "..."'
    Write-Host ""
    exit 1
}

# --- Export ---
if ($Export) {
    Write-Host ""
    Write-Host "Exporting credentials to environment..." -ForegroundColor Cyan
    try {
        $creds = aws configure export-credentials --format env 2>$null
        if ($LASTEXITCODE -ne 0) { throw "export-credentials failed" }
        foreach ($line in $creds) {
            if ($line -match '^export\s+(\w+)=(.+)$') {
                $k = $Matches[1]
                $v = $Matches[2].Trim('"').Trim("'")
                Set-Item -Path "env:$k" -Value $v
                Write-Host "  $k set" -ForegroundColor DarkGray
            }
        }
        $env:AWS_REGION = $region
        Write-Host "  AWS_REGION=$region" -ForegroundColor DarkGray
        Write-Host "Credentials exported to this PowerShell session." -ForegroundColor Green
        Write-Host "These are short-lived. Re-run if you see ExpiredToken." -ForegroundColor Yellow
    } catch {
        Write-Host "Could not export credentials: $_" -ForegroundColor Red
        Write-Host "The aws login session is active so the AWS CLI works," -ForegroundColor Yellow
        Write-Host "but the Anthropic SDK may need explicit env vars." -ForegroundColor Yellow
        Write-Host "Paste credentials from CloudShell instead:" -ForegroundColor Yellow
        Write-Host '  Log into the AWS Console > CloudShell > run:'
        Write-Host '    aws configure export-credentials --format env'
        exit 1
    }
}

Write-Host ""
