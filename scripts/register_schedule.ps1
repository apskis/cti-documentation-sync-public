<#
.SYNOPSIS
  Register the monthly CTI documentation sync with Windows Task Scheduler.

.DESCRIPTION
  Creates a task that fires on the 1st, 2nd and 3rd of every month. The date
  guard inside run_doc_sync.ps1 decides which of those three runs does work,
  which matches how the Claude scheduled task behaved.

  Run this from an elevated PowerShell prompt in the repository root.

.EXAMPLE
  .\scripts\register_schedule.ps1 -At "07:30"
  .\scripts\register_schedule.ps1 -Unregister
#>
[CmdletBinding()]
param(
    [string]$TaskName = "GeneLabs CTI Documentation Sync",
    [string]$At = "07:30",
    [switch]$Unregister
)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$runner = Join-Path $repo "scripts\run_doc_sync.ps1"

if ($Unregister) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path $runner)) { throw "runner not found: $runner" }

$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$runner`"" `
    -WorkingDirectory $repo

# Task Scheduler has no native "first weekday" trigger, so fire on the 1st, 2nd
# and 3rd and let the date guard pick the right one.
$trigger = New-ScheduledTaskTrigger -Monthly -DaysOfMonth 1,2,3 -At $At

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -DontStopOnIdleEnd `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
    -MultipleInstances IgnoreNew

$principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType Interactive `
    -RunLevel Limited

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "Monthly reconciliation of the CTI plans and AI strategy deck against the CTI Deliverables folder. Fires on the 1st, 2nd and 3rd; the date guard runs the work on the first weekday only." `
    -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName"
Write-Host "  Fires   : day 1, 2 and 3 of each month at $At"
Write-Host "  Runs    : $runner"
Write-Host "  Guard   : scripts\date_guard.py, first weekday only"
Write-Host ""
Write-Host "The task runs as $env:USERNAME with an interactive logon, so the"
Write-Host "OneDrive folders are mounted and Word is reachable for PDF rendering."
Write-Host "The machine must be signed in and awake at $At."
