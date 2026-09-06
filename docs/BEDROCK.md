# Running this on Bedrock

The question this repository exists to answer: *I have a Claude API key that
points at a Bedrock model my AWS account has access to. Can I configure the repo
to use it for these tasks inside Cursor?*

The short answer is yes, with one substitution that matters. The long answer is
below, because the substitution is the whole point.

## The short answer

**Yes, through Claude Code.** Claude Code has first class Bedrock support: set
`CLAUDE_CODE_USE_BEDROCK=1`, give it your credentials and a pinned model, and
every skill in this repository runs against your account's Bedrock models. It
runs in Cursor's integrated terminal, so you are working inside Cursor the whole
time. Setup is a wizard, `/setup-bedrock`, or the environment file in `config/`.

**Not reliably through Cursor's own agent.** Cursor does list AWS Bedrock among
its bring your own key providers, so the key will be accepted. But Cursor's
documentation limits custom keys to chat models, and Cursor staff have stated
that agent mode "requires specialized models and features that are fully
supported only for official providers". Agent mode is exactly what runs these
skills. A BYOK Bedrock key in Cursor gives you a chat window, not a working
`/cti-doc-sync`.

So the practical arrangement is: **Cursor as the editor, Claude Code as the
engine, Bedrock as the model.** You lose nothing you were using.

## Why the distinction matters here

The skills in this repository are not prompts you paste into a chat. They drive
a tool loop: list a directory, read a document, run a Python script, edit a
file, render a PDF, look at it, decide, write. That loop is agent mode. A
configuration that gives you a chat model on Bedrock but not a working agent
loop cannot run the monthly sync at all, however good the model is.

That is why this repository routes Bedrock through Claude Code rather than
trying to make Cursor's agent accept the key.

## Setting it up

### 1. Know which credential you actually have

"A Claude API key for Bedrock" can mean three different things, and they are
configured differently.

| What you have | Looks like | Set |
| --- | --- | --- |
| **Bedrock API key** | a long bearer token, issued in the AWS console | `AWS_BEARER_TOKEN_BEDROCK` |
| **IAM access key pair** | `AKIA...` plus a secret | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and `AWS_SESSION_TOKEN` if temporary |
| **SSO or a named profile** | a profile name in `~/.aws/config` | `AWS_PROFILE`, after `aws sso login --profile <name>` |

None of these is an Anthropic API key. An Anthropic key starts `sk-ant-` and
talks to Anthropic's own API, which is a different endpoint, a different bill
and a different account. If what you were handed starts `sk-ant-`, you do not
have Bedrock access, you have direct Anthropic access, and you should leave
`CLAUDE_CODE_USE_BEDROCK` unset and set `ANTHROPIC_API_KEY` instead.

### 2. Fill in the config

```bash
cp config/bedrock.env.example config/bedrock.env
```

Edit it. At minimum you need `CLAUDE_CODE_USE_BEDROCK=1`, `AWS_REGION`, one
credential form, and `ANTHROPIC_MODEL`. The file is gitignored.

Then load it:

```powershell
. .\scripts\load_bedrock_env.ps1     # Windows, dot-sourced
source scripts/load_bedrock_env.sh   # macOS, Linux, WSL
```

Or skip the file entirely and let Claude Code's own wizard write
`~/.claude/settings.json`: run `claude`, choose **3rd-party platform**, then
**Amazon Bedrock**. It detects your AWS profiles, verifies which Claude models
your account can actually invoke, and pins them. `config/claude-settings.example.json`
shows what it produces. The wizard is the better path for a permanent install;
the env file is better for a scripted or shared one.

### 3. Prove it before trusting it

```
python scripts/bedrock_doctor.py            # config and account, no calls
python scripts/bedrock_doctor.py --invoke   # one real, token-billed call
```

The preflight resolves credentials, checks the region, lists the Claude
inference profiles your account can see, confirms your pinned models are among
them, and with `--invoke` makes one sixteen token call to prove the path end to
end. Every failure names its fix.

Run the `--invoke` check before the first sync. A configuration that looks right
and fails at call time wastes a whole run.

### 4. Pin the models. Always.

An unpinned alias resolves to Claude Code's built-in Bedrock default, which is
an Opus class model. Two consequences: it may not be enabled in your account, in
which case the run falls back or fails, and if it is enabled you are billed at
the Opus rate without having chosen it.

```bash
ANTHROPIC_MODEL=us.anthropic.claude-opus-5
ANTHROPIC_DEFAULT_HAIKU_MODEL=us.anthropic.claude-haiku-4-5-20251001-v1:0
```

Start with Opus. This task is judgment heavy and runs twelve times a year, so
the tier matters more than the per-token price. `docs/MODELS.md` has the
reasoning and the fallbacks.

The `us.` prefix is a cross-region inference profile. Use `eu.` or `apac.` for
those geographies and `us-gov.` in GovCloud. If your account exposes models
through an application inference profile instead, use its ARN as the model id.
List what you can actually invoke:

```
aws bedrock list-inference-profiles --region us-west-2
```

### 5. IAM

`config/iam-policy.json` carries the minimum: `InvokeModel`,
`InvokeModelWithResponseStream`, `ListInferenceProfiles`, `GetInferenceProfile`,
plus the marketplace subscription condition. Narrow the resource list to the
specific profile ARNs once you know which ones GeneLabs grants.

`ListInferenceProfiles` is the one people leave out. Without it Claude Code
cannot check a model before using it, so a wrong model id fails at call time
with a 400 instead of at startup with a clear message. The preflight tells you
if it is missing.

## What you give up on Bedrock

Two things, and one of them affects your CTI work directly.

### WebSearch does not work

Claude Code's WebSearch tool is not available through Bedrock. This is a
platform limitation, not a configuration mistake, and nothing in this repository
can work around it.

What that means for each part of this repository:

| Work | Effect |
| --- | --- |
| **The monthly doc sync** | **Unaffected.** It reads the deliverables folder and the state record, both local. It never needed the open web. |
| Hunt reports, run summaries, RTR walkthroughs | Unaffected. They work from Falcon and Splunk output through MCP, not the web. |
| Exposure advisories, detection handoffs | Mostly unaffected. Scan and connector data comes through MCP. |
| **Bulletins, CVE briefs, awareness posts** | **Degraded.** These research current threat activity and cite sources. Without WebSearch the agent cannot fetch a vendor advisory or confirm a CVE's exploitation status itself. |

For the degraded set the workable pattern is to paste the source material into
the session yourself, or keep a second Claude Code profile on direct Anthropic
API access for research and use Bedrock for everything else. Both providers can
coexist on one machine; they are just environment variables.

The doc sync, which is what this repository was built for, runs on Bedrock with
no loss at all.

### Prompt caching may be absent

Prompt caching is not available in every Bedrock region. If cache token counts
stay at zero, that is why, and every run pays full price for the context it
resends. The skills in this repository are long, so this is a real cost
difference rather than a rounding error. Check
[supported regions](https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-caching.html)
before picking one.

## If GeneLabs requires guardrails

Bedrock Guardrails apply content filtering to model traffic, which a security
organization may require for anything touching threat intelligence. Create the
guardrail, publish a version, then pass the headers:

```json
{
  "env": {
    "ANTHROPIC_CUSTOM_HEADERS": "X-Amzn-Bedrock-GuardrailIdentifier: your-id\nX-Amzn-Bedrock-GuardrailVersion: 1"
  }
}
```

Enable cross-region inference on the guardrail if you use cross-region
inference profiles, or it will not apply.

## Why an organization would want this

Worth stating, since the case for the extra setup is not obvious:

- **The traffic stays in GeneLabs's AWS account.** Model calls are billed to and
  logged in infrastructure the security organization already governs, rather
  than a separate vendor account.
- **CloudTrail and existing controls apply.** Invocations are auditable the same
  way other AWS API activity is.
- **Guardrails are enforceable centrally**, not per user.
- **Procurement is already done** if GeneLabs has an AWS agreement, which is
  often the shorter path to approval than a new vendor.

Against that: no WebSearch, possibly no prompt caching, and one more layer that
can misconfigure. The preflight exists to make that last one cheap.

## Troubleshooting

| Symptom | Cause |
| --- | --- |
| `on-demand throughput isn't supported` | You used a bare foundation model id. Use the inference profile id, the one with the `us.` prefix. |
| `AccessDeniedException` on invoke | Model access not granted in the Bedrock console, or the IAM policy is missing `InvokeModel`. |
| `ValidationException` naming the model | The profile does not exist in this region. Check `aws bedrock list-inference-profiles`. |
| `Session token not found or invalid` | An SSO profile whose IAM Identity Center region differs from the Bedrock region, on older Claude Code. Update, or set the region explicitly. |
| Claude Code ignores your Bedrock config | `CLAUDE_CODE_USE_BEDROCK` is not reaching the process. Confirm it is exported in the shell that launched `claude`, or set it in the settings file. |
| Cost higher than expected | An unpinned model resolving to Opus. Pin `ANTHROPIC_MODEL`. |

Confirm what is actually in effect by running `/status` inside a Claude Code
session. It shows the provider and the resolved region.

## Sources

- [Claude Code on Amazon Bedrock](https://code.claude.com/docs/en/amazon-bedrock)
- [Cursor: bring your own API key](https://cursor.com/help/models-and-usage/api-keys)
- [Cursor forum: agent mode in BYOK](https://forum.cursor.com/t/agent-mode-in-byok/147497)
- [Amazon Bedrock API keys](https://docs.aws.amazon.com/bedrock/latest/userguide/api-keys.html)
- [Amazon Bedrock prompt caching](https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-caching.html)
