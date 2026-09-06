# CTI Documentation Sync (Bedrock)

April Parker's CTI production and documentation system, running locally against
**Claude models in GeneLabs's own AWS account through Amazon Bedrock**. Same
skills and same monthly documentation sync as the `claude-sdk` build; what
changes is where the model calls go and who is billed for them.

## The answer, up front

*Can I point this at a Bedrock Claude model and run the tasks inside Cursor?*

**Yes, through Claude Code.** Set `CLAUDE_CODE_USE_BEDROCK=1`, supply your
credentials and a pinned model, and every skill here runs against your account's
Bedrock models. Claude Code runs in Cursor's integrated terminal, so you work
inside Cursor throughout.

**Not reliably through Cursor's own agent.** Cursor does accept a Bedrock key as
bring-your-own-key, but its documentation limits custom keys to chat models and
its staff state that agent mode is fully supported only on official provider
routing. Agent mode is what actually runs these skills, so a BYOK key there
gives you a chat window rather than a working `/cti-doc-sync`.

The working arrangement is **Cursor as the editor, Claude Code as the engine,
Bedrock as the model.**

[`docs/BEDROCK.md`](docs/BEDROCK.md) is the full exploration: the three
credential forms, model pinning, IAM, guardrails, cost, and the one capability
you lose.

## What you lose, stated plainly

**WebSearch does not work on Bedrock.** This is a platform limitation and
nothing here can work around it.

The monthly doc sync is **unaffected**: it reads the deliverables folder and the
state record, both local, and never needed the open web. Hunt and exposure work
is unaffected too, since that data arrives through MCP.

Bulletins, CVE briefs and awareness posts are **degraded**, because they
research current threat activity and cite sources. Paste the source material in,
or keep a second Claude Code profile on direct Anthropic access for research.
Both can live on one machine; they are only environment variables.

Prompt caching is also absent in some Bedrock regions, which makes long skills
cost more. `docs/BEDROCK.md` covers both.

## Why this exists

The sync ran in Anthropic's cloud and reached the OneDrive folders through the
Claude desktop bridge. When the bridge is not there, the run cannot do anything,
which is what happened on 2026-09-01. Running locally puts the agent on the same
machine as the files, so there is no bridge to lose. Pointing it at Bedrock
keeps the model traffic inside GeneLabs's AWS account, where CloudTrail,
guardrails and existing billing already apply.

## Quick start

Open the folder in Cursor, or run `claude` in it, and paste this into the Agent
chat:

```
Set up this repository on my machine. Run the cti-setup skill and walk me
through it. I am at the keyboard, so ask me rather than guessing, especially
about where my CTI folders actually live on this computer.
```

The agent handles dependencies, finds the real OneDrive folder paths on this
machine, writes the config, runs the preflight, proves the branding toolchain
works, and walks you through a read only dry run before anything writes.

To do it by hand instead:

```powershell
.\scripts\bootstrap.ps1                    # venv, dependencies, config check
notepad cti.config.json                    # confirm the two folder paths

copy config\bedrock.env.example config\bedrock.env
notepad config\bedrock.env                 # region, credential, pinned model
. .\scripts\load_bedrock_env.ps1

python scripts\bedrock_doctor.py           # config and account, no calls
python scripts\bedrock_doctor.py --invoke  # one real, token-billed call
.\scripts\run_doc_sync.ps1 -Force -DryRun
```

Or skip the env file and let Claude Code's own wizard write the settings: run
`claude`, choose **3rd-party platform**, then **Amazon Bedrock**, or
`/setup-bedrock` in a session.

macOS, Linux and WSL use `./scripts/bootstrap.sh`, `python3 scripts/doctor.py`
and `./scripts/run_doc_sync.sh --force --dry-run`.

See [`START-HERE.md`](START-HERE.md) and
[`docs/SETUP.md`](docs/SETUP.md).

## What is in here

```
.cursor/skills/     19 skills: setup, the monthly sync, every GeneLabs CTI
                    artifact, and the docx/pptx/xlsx/pdf mechanics they call
.claude/skills/     the same 19, mirrored for Claude Code
.cursor/rules/      house style, path safety, sync policy — always loaded
AGENTS.md           entry point for Cursor
CLAUDE.md           entry point for Claude Code
context/            April's standing context and writing preferences
scripts/            bedrock doctor, env loader, preflight doctor, date guard,
                    backups, survey, PDF render, runners, scheduling, notify
cti.config.json     the two folder paths on this machine (gitignored)
config/             bedrock.env template, Claude settings example, IAM policy
docs/               MODELS.md, BEDROCK.md, architecture and diagrams, setup,
                    migration notes, the original task prompt
```

## How it fits together

![Infrastructure](docs/diagrams/cti-documentation-sync-infrastructure.png)

Everything runs on one machine now. The old arrangement had a gap in it: a
scheduled task in Anthropic's cloud could only reach the OneDrive folders
through the Claude desktop bridge, and when that bridge was absent the run
reached nothing.

[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) carries this diagram and the
run flowchart with the reasoning behind both, and `docs/diagrams/` has PNG and
SVG of each for dropping into a deck.

## The monthly sync

Reconciles three documents against the CTI Deliverables folder, which is the
source of truth for what the portfolio actually contains:

| Document | Change history | Versions |
| --- | --- | --- |
| `CTI_Plan.docx` | Release History | two digit, dates `YYYY.MM.DD` |
| `Threat Hunting Plan.docx` | 12. Revision History | decimal, dates `YYYY-MM-DD` |
| `CTI_AI_Strategy_Evolving.pptx` | none | evolves against evidence |

It edits in place, always backing up first, and makes as few edits as possible. A
run that correctly concludes nothing material happened and changes nothing is a
successful run.

Interactively, type `/cti-doc-sync` in the Cursor Agent chat. On a schedule:

```powershell
.\scripts\register_schedule.ps1 -At "07:30"
```

That fires on the 1st, 2nd and 3rd of each month and the date guard does the work
on the first weekday only, matching the old Claude task exactly.

## Which engine

| | Claude Code | Cursor agent |
| --- | --- | --- |
| Install | `npm install -g @anthropic-ai/claude-code` | comes with the Cursor editor |
| Skills folder | `.claude/skills/` | `.cursor/skills/` |
| Entry point | `CLAUDE.md` | `AGENTS.md` |
| Headless CLI | `claude` | `cursor-agent` |
| **Reaches your Bedrock account** | **yes** | not for agent mode |

On this build the engine choice is not a preference. Claude Code is the one that
routes to Bedrock; Cursor's agent routes through Cursor. The runners default to
`claude` and warn if you force `-Engine cursor` while Bedrock is configured,
because that run will not touch your AWS account.

`.cursor/skills/` is canonical and `.claude/skills/` mirrors it. After editing a
skill, run `python scripts/sync_skills.py`; the runners check for drift and
mirror automatically before every scheduled run.

![Where a request goes](docs/diagrams/cti-documentation-sync-bedrock-routing.png)

## Day to day production

Every other CTI skill came across too, so bulletins, hunts, exposure advisories
and CVE briefs can all be produced here:

```
/genelabs-cti-bulletin          /genelabs-threat-hunt-package
/genelabs-cve-priority-brief    /genelabs-threat-hunt-report
/genelabs-exposure-advisory     /genelabs-hunt-run-summary
/genelabs-detection-handoff     /genelabs-rtr-walkthrough
/genelabs-employee-awareness    /genelabs-exposure-team-briefing
```

Skills that call Splunk or Falcon need those MCP servers configured in Cursor
under Settings, MCP. That configuration did not come across with this
repository.

## Known differences from Claude desktop

Three capabilities have local replacements rather than equivalents, and one bug
was fixed on the way across. [`docs/MIGRATION.md`](docs/MIGRATION.md) covers all
four:

- **No device bridge.** Files are local. The `expectedMtimeMs` protection that
  stopped a run overwriting a concurrent edit is now a rule rather than a
  mechanism; watch it in the first few runs.
- **No push notification.** `scripts/notify.py` gives a desktop toast, an
  optional Teams or Slack webhook, and the run report on disk.
- **No Claude memory.** Standing context lives in `context/` and is updated by
  hand.
- **TLP fixed.** The restyler defaulted to stamping `TLP: AMBER` on internal
  program documentation, contrary to the standing rule that the plans carry no
  TLP at all. The default is now `none`. Check whether the live plans picked up
  an AMBER marking in the 2026-08-21 pass.
