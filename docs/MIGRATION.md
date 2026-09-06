# Migrating off Claude desktop

The monthly CTI documentation sync ran as a Claude scheduled task with the
desktop bridge reaching April's OneDrive folders. On 2026-09-01 that run fired,
passed its date guard, and could not reach the machine, because the task had
been created without device access and no task created from the web or phone can
ever get it. This repository moves the same work to Cursor, where the agent runs
on the machine the files are already on.

## What still needs Claude, and what does not

The repository name says `claude-sdk` because an agent is still required: the
skills are instructions, not programs, and something has to read them and act.
That something can be Claude Code (`npm install -g @anthropic-ai/claude-code`)
or Cursor's own agent. Both read the same skills, from `.claude/skills/` and
`.cursor/skills/` respectively, which `scripts/sync_skills.py` keeps identical.

What is gone is not Claude. It is the Claude *desktop scheduled task* and its
device bridge: the cloud session that fired on a schedule and reached this
machine's files through the desktop app. Everything now runs on the machine the
files are already on.

The Python in `scripts/` is ordinary code and needs no agent at all. The date
guard, backups, preflight, deliverables survey, PDF render and notification all
run standalone.

## What is equivalent

| Claude desktop | Here |
| --- | --- |
| Skills synced to the account | `.cursor/skills/` and `.claude/skills/`, version controlled with the repo |
| Scheduled task, monthly | Windows Task Scheduler or cron, days 1, 2 and 3 |
| Step 0 date guard in the prompt | `scripts/date_guard.py`, exit 10 means stop |
| The stored task prompt | `.cursor/skills/cti-doc-sync/SKILL.md` |
| Standing rules in the system prompt | `.cursor/rules/*.mdc`, always applied |

## What is genuinely different

### 1. No device bridge

`device_list_dir`, `device_stage_files`, `device_commit_files` and `device_bash`
do not exist and are not needed. The agent runs on the machine the folders are
on, so it reads and writes them directly.

This removes the staging and commit dance, and with it the `expectedMtimeMs`
protection that stopped the old flow overwriting an edit April made while the run
was in flight. That protection is now a rule rather than a mechanism:
`.cursor/rules/10-paths-and-safety.mdc` requires checking the modification time
before and after, and refusing to write past a Word lock file. Watch this in the
first few runs. If it proves too soft, the honest fix is to teach
`backup_doc.py` to record the mtime and add a `commit_doc.py` that refuses to
write when it moved.

### 2. No push notification

The old run pushed to April's phone and inbox. There is no push channel from a
local process. `scripts/notify.py` gives:

- a desktop toast on Windows, which only helps if she is at the machine
- an optional Teams or Slack incoming webhook, set `CTI_NOTIFY_WEBHOOK`
- the run report written to `<documentation>/_doc_sync/runs/<date>-doc-sync.md`,
  which is the durable record and syncs through OneDrive

The webhook is the closest thing to the old behaviour and is worth setting up.
Without it, a run that finds something urgent will sit unread until she opens
the folder.

### 3. No Claude memory

`/areas/cti-doc-sync-task.md` and `/preferences.md` were read from Claude's
memory filesystem. Cursor has no equivalent, so both are now files in
`context/`, loaded by the rules. They are no longer updated automatically: when
a standing decision changes, edit the file.

### 4. The run is only as reliable as the machine

A cloud scheduled task fires whether or not the laptop is on. Task Scheduler
does not. The registered task uses `-StartWhenAvailable`, so a missed run fires
at the next opportunity, but the machine must be signed in and awake within
reach of the schedule. Check `runs/` if a month goes quiet.

## Fixed on the way across

The restyler defaulted `--tlp` to `AMBER` and always wrote a TLP into the
footer, while April's standing rule is that internal program documentation
carries no TLP marking at all. The task prompt omitted the flag, which silently
selected `AMBER` rather than omitting the marking. In this repository the
default is `none` and `build_footer` skips the TLP runs entirely when it is
`none`, falling back to the marking text alone.

**Worth checking by hand:** whether the live `CTI_Plan.docx` and
`Threat Hunting Plan.docx` currently carry a TLP marking in the footer from the
2026-08-21 pass. If they do, it should come off in the next sync.
