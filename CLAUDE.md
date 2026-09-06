<!--
CLAUDE.md is the Claude Code entry point. AGENTS.md is the Cursor entry point.
They carry the same content; edit both when you change one.
-->

# CTI Documentation Sync (Bedrock)

This repository is April Parker's CTI production and documentation system,
running locally under Claude Code against Amazon Bedrock. It carries the skills that build
every CTI artifact and the monthly sync that keeps the program documentation
honest.

For how the pieces fit together and what the monthly run actually does, see
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md). It carries three diagrams: where
a model call goes and why only Claude Code reaches Bedrock, what reaches the
files on this machine, and a flowchart of the run keyed to the step numbers in
the `cti-doc-sync` skill.

## Orientation

| Path | What it is |
| --- | --- |
| `.cursor/skills/` | The skills. One folder each, `SKILL.md` plus scripts and assets. |
| `.cursor/rules/` | Standing rules the agent always loads. House style, paths, safety. |
| `context/` | April's standing context and preferences, carried over from Claude memory. |
| `scripts/` | Shared tooling: preflight doctor, path resolution, date guard, backups, PDF render, runners. |
| `cti.config.json` | The two folder paths on this machine. Gitignored, one per install. |
| `runs/` | Local run logs. The substantive run reports go to the documentation folder. |
| `config/` | Bedrock env template, Claude settings example, IAM policy. `bedrock.env` itself is gitignored. |
| `docs/MODELS.md` | Which models the task needs and why. Two roles: a vision capable driver, and a cheap background model. |
| `docs/diagrams/` | Mermaid sources plus rendered PNG and SVG. Edit the `.mmd`, then run `scripts/render_diagrams.sh`. |

## Before you do anything

0. If anything looks unconfigured, run `python scripts/doctor.py` and
   `python scripts/bedrock_doctor.py`. They report what is ready and name the
   fix for what is not, and change nothing.
1. Read `context/preferences.md`. It governs how every sentence is written.
2. Resolve paths through `scripts/cti_paths.py` or `cti.config.json`. Never hard
   code a folder.
3. Check `.cursor/rules/00-house.mdc` for the branding standard and the files
   that are off limits.

## The skills

**Setup**

- `cti-setup` — install this repository on a machine. Run it on a fresh clone,
  when the preflight fails, or when the folders move.

**Program documentation**

- `cti-doc-sync` — the monthly reconciliation. Start here for the sync.
- `genelabs-cti-documentation` — build or restyle any CTI program document.

**Intelligence products**

- `genelabs-cti-bulletin` — threat bulletins.
- `genelabs-cve-priority-brief` — the daily VM priority brief.
- `genelabs-employee-awareness`, `genelabs-employee-awareness-blog` — all
  employee posts.

**Hunting**

- `genelabs-threat-hunt-package` — the hunt work order, before it runs.
- `genelabs-threat-hunt-report` — the completed hunt record.
- `genelabs-hunt-run-summary` — the day level roll up across a hunt loop.
- `genelabs-rtr-walkthrough` — manual Falcon console steps for an analyst.
- `genelabs-splunk-spl` — house rules and linter for every SPL query.

**Exposure**

- `genelabs-exposure-advisory` — a single exposed asset, handed to its owner.
- `genelabs-exposure-team-briefing` — the weekly roll up across open advisories.
- `genelabs-detection-handoff` — detection logic handed to the SOC.

**Format helpers**

- `docx`, `pptx`, `xlsx`, `pdf` — the document mechanics the skills above call.

## Bedrock

This build routes model calls to Claude models in GeneLabs's AWS account through
Amazon Bedrock. That works through **Claude Code**, which has first class
Bedrock support. It does **not** work through Cursor's own agent: Cursor accepts
a Bedrock BYOK key for chat models but does not fully support agent mode on
custom keys, and agent mode is the tool loop these skills need.

Configuration lives in `config/bedrock.env`, gitignored because it holds
credentials. Verify it before trusting a run:

```
python scripts/bedrock_doctor.py            # config and account, no calls
python scripts/bedrock_doctor.py --invoke   # one real, token-billed call
```

Two consequences you must respect when working here:

- **WebSearch is unavailable on Bedrock.** Do not plan a skill run around
  fetching a page. The doc sync, hunts and exposure work are unaffected because
  their inputs are local or arrive through MCP. Bulletins and CVE briefs need
  their sources supplied.
- **Models must stay pinned.** An unpinned alias resolves to an Opus class
  default that may not be enabled in the account and is billed at the Opus rate.
  `ANTHROPIC_MODEL` is set in `config/bedrock.env`; leave it set.

[`docs/BEDROCK.md`](docs/BEDROCK.md) has the full picture.

## Two engines

The skills in this repository are Agent Skills, and both Cursor and Claude Code
read that format. The same skill runs either way; only the folder they are
discovered from differs.

| Engine | Skills folder | Entry point | Headless CLI | Reaches Bedrock |
| --- | --- | --- | --- | --- |
| Claude Code | `.claude/skills/` | `CLAUDE.md` | `claude` | **yes** |
| Cursor agent | `.cursor/skills/` | `AGENTS.md` | `cursor-agent` | no, chat only |

`.cursor/skills/` is canonical. `.claude/skills/` is a mirror of it, kept
identical by `scripts/sync_skills.py`. After editing any skill:

```
python scripts/sync_skills.py          # mirror the change across
python scripts/sync_skills.py --check  # verify, exits 1 on drift
```

The runners accept `-Engine claude` or `-Engine cursor` (`--engine` on the shell
script). With neither, they use whichever CLI is installed, preferring `claude`.

## How work runs here

Interactively, open this folder in Cursor or start Claude Code in it, and invoke
a skill with `/`, for example `/cti-doc-sync`. Both discover their skills folder
at startup.

Headless, for the scheduler:

```
.\scripts\run_doc_sync.ps1                    # Windows, auto-detects the engine
.\scripts\run_doc_sync.ps1 -Engine claude     # force Claude Code
./scripts/run_doc_sync.sh --engine cursor     # force Cursor
```

## What changed moving off Claude desktop

Three capabilities do not exist here and have local replacements. `docs/MIGRATION.md`
covers them in full:

- The device bridge is gone. Files are local, so read and write them directly.
- Push notification is gone. `scripts/notify.py` raises a desktop toast and,
  optionally, a Teams or Slack webhook.
- Claude memory is gone. The standing context lives in `context/`, and the
  portfolio state record stays beside the documents it describes.
