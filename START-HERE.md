# Start here

## This build talks to Bedrock

Model calls go to Claude models in GeneLabs's AWS account rather than to
Anthropic directly. That works through **Claude Code**, not through Cursor's own
agent: Cursor accepts a Bedrock key for chat but does not fully support agent
mode on custom keys, and agent mode is what runs these skills.

So: Cursor as the editor, Claude Code as the engine, Bedrock as the model. Read
[`docs/BEDROCK.md`](docs/BEDROCK.md) before setting up, especially the section
on what you lose. The short version is that the monthly doc sync is unaffected
and web research is not available.

## You need an agent to run this

The skills here are Agent Skills. They are instructions, not programs: something
has to read them and act. Two things can, and this repository supports both.

| | Claude Code | Cursor |
| --- | --- | --- |
| Install | `npm install -g @anthropic-ai/claude-code` | comes with the Cursor editor |
| Skills folder | `.claude/skills/` | `.cursor/skills/` |
| Entry point | `CLAUDE.md` | `AGENTS.md` |
| Headless CLI | `claude` | `cursor-agent` |

The two skills folders are mirrors of each other, kept identical by
`scripts/sync_skills.py`. Use whichever engine you prefer, or both; the runners
auto-detect and prefer `claude`.

The Python scripts in `scripts/` are ordinary programs and need neither.

## Setting up

Two ways in. The first is shorter.

## Let the agent set it up

1. Unzip this folder somewhere on the local disk, not inside the OneDrive CTI
   folders.
2. Open the folder in Cursor (File, Open Folder), or run `claude` in it.
3. In the Agent chat, paste this:

```
Set up this repository on my machine. Run the cti-setup skill and walk me
through it, including the Bedrock configuration. I am at the keyboard, so ask
me rather than guessing, especially about where my CTI folders actually live
and which AWS credential form I have.
```

The agent installs the dependencies, configures and proves the Bedrock
connection, searches this machine for the real
`CTI Deliverables` and `CTI Documentation` folders, writes `cti.config.json`,
runs the preflight, proves the branding toolchain works on a scratch document,
walks you through a read only dry run, and offers to register the monthly
schedule. It asks before anything that changes your machine.

If typing `/cti-setup` does not offer the skill, the engine may not be reading
the skills folder. Paste this instead:

```
Read .cursor/skills/cti-setup/SKILL.md and follow it to set this repository up
on my machine. Ask me rather than guessing about folder paths.
```

On Claude Code the same file is at `.claude/skills/cti-setup/SKILL.md`.

## Or do it by hand

```powershell
.\scripts\bootstrap.ps1                    # venv, dependencies, config check
notepad cti.config.json                    # confirm the two folder paths

copy config\bedrock.env.example config\bedrock.env
notepad config\bedrock.env                 # region, credential, pinned model
. .\scripts\load_bedrock_env.ps1

python scripts\bedrock_doctor.py --invoke  # prove the Bedrock path works
.\scripts\run_doc_sync.ps1 -Force -DryRun
```

macOS, Linux and WSL use `./scripts/bootstrap.sh`, `python3 scripts/doctor.py`
and `./scripts/run_doc_sync.sh --force --dry-run`.

Full walkthrough: [`docs/SETUP.md`](docs/SETUP.md).

## Seeing how it works

[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) has an infrastructure diagram and
a flowchart of the monthly run. Worth two minutes before the first run: the
flowchart shows the four places a run can correctly end without changing
anything.

## Two things to know before the first run

**The path in the example config is a guess.** It is the path from the old
machine. OneDrive tenant folder names vary, so the setup skill searches for the
folders rather than trusting it.

**The first run has a month of drift to absorb.** The September 2026 scheduled
run fired, passed its date guard, and could not reach the machine, so nothing was
reconciled. Read the dry run output properly before letting it write.
