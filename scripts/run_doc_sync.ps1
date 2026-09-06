<#
.SYNOPSIS
  Headless monthly CTI documentation sync.

.DESCRIPTION
  Runs the date guard, then hands the cti-doc-sync skill to an agent CLI in non
  interactive mode. Intended to be called by Task Scheduler on the 1st, 2nd and
  3rd of each month; the guard decides which of those three runs does work.

  Either engine works. Claude Code reads .claude/skills, Cursor reads
  .cursor/skills, and scripts/sync_skills.py keeps the two identical.

.EXAMPLE
  .\scripts\run_doc_sync.ps1                    # auto-detect, prefers claude
  .\scripts\run_doc_sync.ps1 -Engine cursor     # force Cursor
  .\scripts\run_doc_sync.ps1 -Force             # ignore the date guard
  .\scripts\run_doc_sync.ps1 -Force -DryRun     # report only, change nothing
#>
[CmdletBinding()]
param(
    [switch]$Force,
    [switch]$DryRun,
    [ValidateSet("auto", "claude", "cursor")]
    [string]$Engine = "auto",
    # Start with Opus: this task is judgment heavy. Resolved below, because on
    # Bedrock the ANTHROPIC_MODEL pin governs and a bare alias would override it.
    [string]$Model = "",
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

$logDir = Join-Path $repo "runs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$stamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
$log = Join-Path $logDir "$stamp-doc-sync.log"

function Write-Log($msg) {
    $line = "{0}  {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $msg
    Write-Host $line
    Add-Content -Path $log -Value $line
}

Write-Log "CTI documentation sync starting in $repo"

if (-not $Force) {
    $guardOut = & $Python (Join-Path $repo "scripts\date_guard.py")
    $guard = $LASTEXITCODE
    Write-Log ($guardOut -join " ")
    if ($guard -eq 10) {
        Write-Log "Not the first weekday of the month. No action taken."
        exit 0
    }
    if ($guard -ne 0) {
        Write-Log "Date guard failed with exit code $guard. Stopping."
        exit $guard
    }
} else {
    Write-Log "Date guard bypassed with -Force."
}

# Bedrock configuration, if this install uses it.
if (Test-Path (Join-Path $repo "config\bedrock.env")) {
    . (Join-Path $repo "scripts\load_bedrock_env.ps1") | Out-Null
    Write-Log "Bedrock config loaded: region $($env:AWS_REGION), model $($env:ANTHROPIC_MODEL)"
}

# Keep the two skills folders identical before handing work to either engine.
& $Python (Join-Path $repo "scripts\sync_skills.py") --check | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Log "Skills folders had drifted; mirroring .cursor/skills to .claude/skills."
    & $Python (Join-Path $repo "scripts\sync_skills.py") | Out-Null
}

function Resolve-Engine($choice) {
    $claude = Get-Command "claude" -ErrorAction SilentlyContinue
    $cursor = (Get-Command "cursor-agent" -ErrorAction SilentlyContinue),
              (Get-Command "agent" -ErrorAction SilentlyContinue) |
              Where-Object { $_ } | Select-Object -First 1
    switch ($choice) {
        "claude" {
            if (-not $claude) {
                Write-Log "ERROR Claude Code CLI not found. Install it with: npm install -g @anthropic-ai/claude-code"
                exit 127
            }
            return @{ Name = "claude"; Path = $claude.Source }
        }
        "cursor" {
            if (-not $cursor) {
                Write-Log "ERROR Cursor CLI not found. Install it with: irm 'https://cursor.com/install?win32=true' | iex"
                exit 127
            }
            if ($env:CLAUDE_CODE_USE_BEDROCK -eq "1") {
                Write-Log "WARNING Bedrock is configured, but the Cursor engine does not use it."
                Write-Log "        Cursor routes through its own account, or through a BYOK key"
                Write-Log "        set in the Cursor UI, and its agent mode is not fully"
                Write-Log "        supported on custom keys. See docs/BEDROCK.md."
            }
            return @{ Name = "cursor"; Path = $cursor.Source }
        }
        default {
            if ($claude) { return @{ Name = "claude"; Path = $claude.Source } }
            if ($cursor) { return @{ Name = "cursor"; Path = $cursor.Source } }
            Write-Log "ERROR no agent CLI on PATH. Install one:"
            Write-Log "  Claude Code : npm install -g @anthropic-ai/claude-code"
            Write-Log "  Cursor      : irm 'https://cursor.com/install?win32=true' | iex"
            exit 127
        }
    }
}

$eng = Resolve-Engine $Engine

# Resolve the model request now that the Bedrock config, if any, is loaded.
if (-not $Model) {
    if ($env:CLAUDE_CODE_USE_BEDROCK -eq "1" -or $env:ANTHROPIC_MODEL) {
        # A pinned inference profile is already in effect. Passing -Model opus
        # here would replace that pin with an alias Bedrock resolves on its own,
        # which is the exact thing docs/MODELS.md tells you not to do.
        Write-Log "Model: pinned by ANTHROPIC_MODEL=$($env:ANTHROPIC_MODEL)"
    } else {
        $Model = "opus"
        Write-Log "Model: opus (default for this task)"
    }
} else {
    Write-Log "Model: $Model (explicit)"
}

$prompt = @"
Run the cti-doc-sync skill for this month.

The date guard has already passed, so do not run it again. Follow the skill from
Step 1 through Step 8. Nobody is watching this run: do not ask questions, make
the conservative choice where a judgment call is needed, and flag it under items
requiring human review in the run summary.
"@

if ($DryRun) {
    $prompt += "`n`nDRY RUN: analyse and report only. Do not edit, back up, or write any file inside the documentation folder. Print the run summary to stdout instead."
}

if ($eng.Name -eq "claude") {
    $agentArgs = @("-p", $prompt)
    if (-not $DryRun) { $agentArgs += @("--permission-mode", "acceptEdits") }
    if ($Model) { $agentArgs += @("--model", $Model) }
} else {
    $agentArgs = @("-p", $prompt, "--output-format", "text")
    if ($Model) { $agentArgs += @("--model", $Model) }
}

Write-Log "Engine: $($eng.Name) at $($eng.Path)"
& $eng.Path @agentArgs 2>&1 | Tee-Object -FilePath $log -Append
$code = $LASTEXITCODE

Write-Log "Agent exited with code $code"

if ($code -ne 0) {
    & $Python (Join-Path $repo "scripts\notify.py") `
        --title "CTI doc sync FAILED" `
        --message "The monthly CTI documentation sync exited with code $code. Engine: $($eng.Name). Log: $log"
}

exit $code
