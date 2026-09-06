# Models this task needs

The CTI Documentation Sync is an agentic run, not a single prompt. That sets
three hard requirements on whatever model drives it, and one soft one. Get the
capabilities right and the model choice is mostly a cost decision; get them
wrong and the run fails in ways that are hard to spot, because a model that
cannot see a PDF will still tell you the branding looks fine.

## The short list

| # | Role | Needed? | Bedrock inference profile |
| :-: | --- | --- | --- |
| 1 | **Primary driver** | **Required** | `us.anthropic.claude-opus-5` |
| 2 | **Background / small fast** | Recommended | `us.anthropic.claude-haiku-4-5-20251001-v1:0` |

Two models. That is the whole list. Everything else in this repository is
deterministic Python and needs no model at all.

## 1. The primary driver

This is the model that reads the state record, walks the deliverables tree,
decides material versus routine, edits the documents, and checks its own work.

It must have all four of these:

| Capability | Why the task needs it |
| --- | --- |
| **Agentic tool use** | The run is dozens of turns: list, read, run a script, edit, render, look, decide. A chat-only model cannot do it at all. |
| **Vision** | Step 3b renders the document to PDF and looks at it. Four skills depend on this, and it is the only check that catches a broken banner or a stray heading number. |
| **Long context** | The skill, three always-on rules, the standing context, the state record and a survey of a large deliverables tree, all in one session. |
| **Instruction adherence** | The rule that earns its keep is *do not edit unless something material changed*. A model that drifts toward being helpful will manufacture edits, which is the exact failure this task was designed to avoid. |

Pick one, in descending order of judgment and cost:

**Start with Opus.** The work this task does is judgment, not volume: deciding
whether a month of portfolio movement is material, deciding whether a claim
traces to evidence, deciding when to change nothing. Those are exactly the calls
where model tier shows, and the run happens twelve times a year over a bounded
input, so the cost argument for a cheaper tier is weak against the cost of a
wrong call landing in a governance document.

| Model | Bedrock ID | When to pick it |
| --- | --- | --- |
| **Claude Opus 5** | **`us.anthropic.claude-opus-5`** | **The default. Start here.** Best judgment on the material versus routine call and on the Step 6 traceability check. |
| Claude Opus 4.8 | `us.anthropic.claude-opus-4-8` | Same class, if 5 is not enabled in your account. |
| Claude Sonnet 4.6 | `us.anthropic.claude-sonnet-4-6` | Fallback when no Opus is enabled in the account, or for a dry run where you only want to see what it finds. |
| Claude Sonnet 4.5 | `us.anthropic.claude-sonnet-4-5-20250929-v1:0` | Workable minimum. |

Anything below Sonnet class is not worth trying. The judgment calls in Step 2
and Step 6 are the point of the task, and a cheaper model reaches them by
guessing.

If you drop to Sonnet for a run, say so in the run summary. A month reconciled
by a lower tier is worth knowing about when you next read the state record.

## 2. The background model

Claude Code runs small side tasks, session titles and similar, on a separate
model. On Bedrock it defaults to the **Sonnet** model for these, because Haiku
is not enabled in every account. That works, and it costs more than it needs to.

Enabling Haiku and pinning it moves that traffic to the cheap model:

```
ANTHROPIC_DEFAULT_HAIKU_MODEL=us.anthropic.claude-haiku-4-5-20251001-v1:0
```

Recommended, not required. Skip it if getting a second model approved is more
friction than the saving is worth.

## Pin them. Always.

Pinning is not about avoiding Opus, it is about choosing it deliberately. An
unpinned alias resolves to Claude Code's built-in Bedrock default, which may not
be enabled in your account, and which changes as new versions ship. Pin the Opus
version you want and you get that model every run, rather than whichever one the
default happens to point at this month.

```
ANTHROPIC_MODEL=us.anthropic.claude-opus-5
ANTHROPIC_DEFAULT_HAIKU_MODEL=us.anthropic.claude-haiku-4-5-20251001-v1:0
```

## How the runners pick

`run_doc_sync` resolves the model in one place so the two setups do not fight:

| Situation | What it does |
| --- | --- |
| Bedrock configured (`CLAUDE_CODE_USE_BEDROCK=1` or `ANTHROPIC_MODEL` set) | Passes no `--model`. The pin governs, which is the point of pinning. |
| No Bedrock config | Passes `--model opus`. |
| `--model` / `-Model` given explicitly | Uses it, and logs that it was explicit. |

The first row matters more than it looks. Passing `--model opus` on Bedrock
would replace your pinned inference profile with a bare alias, and an alias is
not a pin: Bedrock resolves it to its own default, which may be a different
version or one your account cannot invoke. The runner logs which branch it took
on every run.

## Verify before you trust it

Enabling a model in the Bedrock console is not the same as being able to invoke
it. Check what your account and region can actually reach:

```
aws bedrock list-inference-profiles --region $AWS_REGION
python scripts/bedrock_doctor.py            # confirms your pins are invocable
python scripts/bedrock_doctor.py --invoke   # one real call, end to end
```

The preflight fails on a pinned model that is not in the list and names the
closest one it can see.

## Prefixes and regions

`us.` is a cross-region inference profile. Use `eu.` or `apac.` for those
geographies and `us-gov.` in GovCloud. A bare foundation model id without a
prefix produces `on-demand throughput isn't supported`; that error means you
need the inference profile id, not a different model.

If your account exposes models through an **application inference profile**,
use its ARN as the model id instead and ignore the prefixes entirely.

## The 1M context variant

Claude Opus 4.6 and later, Sonnet 5 and Sonnet 4.6 support a 1M token context
window on Bedrock. Append `[1m]` to the pinned id to select it:

```
ANTHROPIC_MODEL=us.anthropic.claude-opus-5[1m]
```

You almost certainly do not need this. The sync surveys the deliverables tree
with counts and newest-per-class rather than reading every file, which is what
`scripts/survey_deliverables.py` is for. Reach for the 1M variant only if a run
actually exhausts context, and treat that as a signal the survey step is pulling
in too much.

## What you do not need

- **No embedding model.** Nothing here does vector search.
- **No image generation model** for this task. Only the awareness blog skill
  wants illustrations, and that is a different job.
- **No separate model for the scripts.** The date guard, backups, deliverables
  survey, PDF render, preflight and notification are ordinary Python.

## If you are not on Bedrock

The same two roles apply, with plain model names instead of inference profiles.
The capability requirements do not change: the driver still needs tool use,
vision, long context and the discipline to change nothing when nothing changed.

## One thing to watch on Bedrock

WebSearch is unavailable through Bedrock. **The doc sync is unaffected** because
its inputs are local. But no choice of model restores it, so do not read a
research failure in another skill as a sign you picked the wrong model. See
[`BEDROCK.md`](BEDROCK.md).
