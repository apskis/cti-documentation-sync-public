# Setting up

Written for Cursor, but every step works the same under Claude Code. Where this
page says Cursor, substitute `claude` for `cursor-agent` and `.claude/skills`
for `.cursor/skills`.

**The fast path is to let the agent do this.** Open the folder in Cursor and
paste into the Agent chat:

```
Set up this repository on my machine. Run the cti-setup skill and walk me
through it. I am at the keyboard, so ask me rather than guessing, especially
about where my CTI folders actually live on this computer.
```

The `cti-setup` skill covers everything below, and unlike this page it searches
the machine for the real folder paths rather than trusting the example. What
follows is the same sequence done by hand.

## 1. Put the repository somewhere sensible

Anywhere on the local disk. Do not put it inside the OneDrive CTI folders: the
repository is tooling, those folders are content, and mixing them means the sync
run walks its own source code.

A reasonable choice on Windows:

```
C:\Users\<user>\src\cti-documentation-sync-claude-sdk
```

## 2. Run the bootstrap

```powershell
cd C:\Users\<user>\src\cti-documentation-sync-claude-sdk
.\scripts\bootstrap.ps1
```

It creates `.venv`, installs the Python dependencies, copies
`cti.config.example.json` to `cti.config.json`, and checks that both configured
folders resolve.

## 3. Point the config at the real folders

Open `cti.config.json` and confirm the two paths. Forward slashes are fine on
Windows and avoid escaping trouble in JSON:

```json
{
  "deliverables": "C:/Users/<user>/GeneLabs LLC/Security Operations Center - CTI/CTI Deliverables",
  "documentation": "C:/Users/<user>/GeneLabs LLC/Security Operations Center - CTI/CTI Documentation"
}
```

Re run the bootstrap until both report OK.

The path in the example is the one from the old machine. OneDrive tenant folder
names vary between machines and accounts, so treat it as a starting guess. To
find the real ones:

```powershell
Get-ChildItem "$env:USERPROFILE" -Directory -Recurse -Depth 3 -ErrorAction SilentlyContinue |
    Where-Object Name -in "CTI Deliverables","CTI Documentation" |
    Select-Object FullName
```

If OneDrive shows the folders as online only placeholders, mark the CTI folder
"Always keep on this device". The sync needs the files locally available.

## 4. Open the folder in Cursor

Cursor discovers skills in `.cursor/skills` at startup and rules in
`.cursor/rules`. Confirm both loaded:

- Type `/` in the Agent chat. `cti-doc-sync` and the `genelabs-*` skills should
  be listed.
- Settings, Rules, should show the three project rules, two of them always
  applied.

If skills do not appear, check the Cursor version. Agent Skills need a build
that supports `.cursor/skills`; older builds only read `.cursor/rules`. On an
older build, the fallback is to `@` mention the SKILL.md file you want.

## 5. Preflight

```powershell
python scripts\doctor.py
```

Ten to twenty checks covering Python, dependencies, skills, rules, both folders,
each maintained document, the state record, backup folder, Word lock files, the
Cursor CLI, the PDF renderer and the notification webhook. It changes nothing and
names the fix for anything wrong. Resolve every FAIL before a real run.

Two warnings are normal on a fresh install: the Cursor CLI is only needed for
scheduled runs, and the notification webhook is optional.

A missing `portfolio_state.md` is a FAIL worth pausing on. It is the comparison
baseline for every sync, and a run without it must not invent one from file
timestamps.

## 6. First run, read only

```powershell
.\scripts\run_doc_sync.ps1 -Force -DryRun
```

`-Force` skips the date guard so you can run it today. `-DryRun` tells the agent
to analyse and report without writing anything. Read the output and confirm it
found the deliverables tree, read the state record, and reached sensible
conclusions before you let it write.

## 7. First real run

```powershell
.\scripts\run_doc_sync.ps1 -Force
```

Then look at what it did: the backups in `_doc_sync/backups/`, the run report in
`_doc_sync/runs/`, and the rendered PDFs.

## 8. Schedule it

From an elevated PowerShell prompt:

```powershell
.\scripts\register_schedule.ps1 -At "07:30"
```

That fires on the 1st, 2nd and 3rd of each month; the date guard runs the work on
the first weekday only, which is exactly what the Claude task did. Scheduled
runs need the Cursor CLI on PATH:

```powershell
irm 'https://cursor.com/install?win32=true' | iex
```

To remove it later:

```powershell
.\scripts\register_schedule.ps1 -Unregister
```

## 9. Optional, notification

Set a Teams or Slack incoming webhook so run summaries reach you when you are
not at the machine:

```powershell
[Environment]::SetEnvironmentVariable("CTI_NOTIFY_WEBHOOK", "https://...", "User")
```

Without it, notification is a desktop toast plus the run report file.

## Using the other skills

The same repository carries every CTI skill, so day to day production works here
too. In the Agent chat:

```
/genelabs-cti-bulletin        draft a bulletin
/genelabs-threat-hunt-package turn findings into a runnable hunt plan
/genelabs-cve-priority-brief  build the daily VM brief
/genelabs-exposure-advisory   write up an exposed asset
```

Skills that call an external system, Splunk and Falcon among them, need those
MCP servers configured in Cursor under Settings, MCP. That configuration did not
come across with this repository.
