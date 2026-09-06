#!/usr/bin/env bash
# Headless monthly CTI documentation sync, for macOS, Linux and WSL.
#
# Either engine works. Claude Code reads .claude/skills, Cursor reads
# .cursor/skills, and scripts/sync_skills.py keeps the two identical.
#
#   ./scripts/run_doc_sync.sh                      auto-detect, prefers claude
#   ./scripts/run_doc_sync.sh --engine cursor      force Cursor
#   ./scripts/run_doc_sync.sh --force              ignore the date guard
#   ./scripts/run_doc_sync.sh --force --dry-run    report only, change nothing
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"

PYTHON="${PYTHON:-python3}"
FORCE=0
DRY_RUN=0
ENGINE="${CTI_AGENT_ENGINE:-auto}"
# Start with Opus: this task is judgment heavy.
# On Bedrock the pin in ANTHROPIC_MODEL selects the model and a bare alias would
# override it with something that is NOT a pin, so leave MODEL empty there.
# Off Bedrock, the alias is the right way to ask for Opus. Override with --model.
MODEL="${CTI_AGENT_MODEL:-}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --force)   FORCE=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    --engine)  ENGINE="$2"; shift 2 ;;
    --model)   MODEL="$2"; shift 2 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

mkdir -p runs
LOG="runs/$(date +%Y-%m-%d_%H%M%S)-doc-sync.log"
log() { printf '%s  %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" | tee -a "$LOG"; }

log "CTI documentation sync starting in $REPO"

if [[ $FORCE -eq 0 ]]; then
  set +e
  GUARD_OUT="$($PYTHON scripts/date_guard.py)"
  GUARD=$?
  set -e
  log "$GUARD_OUT"
  if [[ $GUARD -eq 10 ]]; then
    log "Not the first weekday of the month. No action taken."
    exit 0
  elif [[ $GUARD -ne 0 ]]; then
    log "Date guard failed with exit code $GUARD. Stopping."
    exit $GUARD
  fi
else
  log "Date guard bypassed with --force."
fi

# Bedrock configuration, if this install uses it.
if [[ -f config/bedrock.env ]]; then
  # shellcheck disable=SC1091
  source scripts/load_bedrock_env.sh >/dev/null 2>&1 || true
  log "Bedrock config loaded: region ${AWS_REGION:-unset}, model ${ANTHROPIC_MODEL:-unpinned}"
fi

# Keep the two skills folders identical before handing work to either engine.
if ! $PYTHON scripts/sync_skills.py --check >/dev/null 2>&1; then
  log "Skills folders had drifted; mirroring .cursor/skills to .claude/skills."
  $PYTHON scripts/sync_skills.py >/dev/null
fi

CLAUDE_BIN="$(command -v claude || true)"
CURSOR_BIN="$(command -v cursor-agent || command -v agent || true)"

case "$ENGINE" in
  claude)
    [[ -n "$CLAUDE_BIN" ]] || { log "ERROR Claude Code CLI not found. Install: npm install -g @anthropic-ai/claude-code"; exit 127; }
    ENGINE_NAME=claude; AGENT="$CLAUDE_BIN" ;;
  cursor)
    [[ -n "$CURSOR_BIN" ]] || { log "ERROR Cursor CLI not found. Install: curl https://cursor.com/install -fsS | bash"; exit 127; }
    if [[ "${CLAUDE_CODE_USE_BEDROCK:-}" == "1" ]]; then
      log "WARNING Bedrock is configured, but the Cursor engine does not use it."
      log "        Cursor routes through its own account, or through a BYOK key"
      log "        set in the Cursor UI, and its agent mode is not fully"
      log "        supported on custom keys. See docs/BEDROCK.md."
    fi
    ENGINE_NAME=cursor; AGENT="$CURSOR_BIN" ;;
  auto)
    if [[ -n "$CLAUDE_BIN" ]]; then ENGINE_NAME=claude; AGENT="$CLAUDE_BIN"
    elif [[ -n "$CURSOR_BIN" ]]; then ENGINE_NAME=cursor; AGENT="$CURSOR_BIN"
    else
      log "ERROR no agent CLI on PATH. Install one:"
      log "  Claude Code : npm install -g @anthropic-ai/claude-code"
      log "  Cursor      : curl https://cursor.com/install -fsS | bash"
      exit 127
    fi ;;
  *) log "ERROR unknown engine: $ENGINE (use claude, cursor or auto)"; exit 2 ;;
esac

# Resolve the model request now that the Bedrock config, if any, is loaded.
if [[ -z "$MODEL" ]]; then
  if [[ "${CLAUDE_CODE_USE_BEDROCK:-}" == "1" || -n "${ANTHROPIC_MODEL:-}" ]]; then
    # A pinned inference profile is already in effect. Passing --model opus here
    # would replace that pin with an alias Bedrock resolves on its own, which is
    # the exact thing docs/MODELS.md tells you not to do.
    log "Model: pinned by ANTHROPIC_MODEL=${ANTHROPIC_MODEL:-unset}"
  else
    MODEL="opus"
    log "Model: opus (default for this task)"
  fi
else
  log "Model: $MODEL (explicit)"
fi

PROMPT="Run the cti-doc-sync skill for this month.

The date guard has already passed, so do not run it again. Follow the skill from
Step 1 through Step 8. Nobody is watching this run: do not ask questions, make
the conservative choice where a judgment call is needed, and flag it under items
requiring human review in the run summary."

if [[ $DRY_RUN -eq 1 ]]; then
  PROMPT="$PROMPT

DRY RUN: analyse and report only. Do not edit, back up, or write any file inside
the documentation folder. Print the run summary to stdout instead."
fi

if [[ "$ENGINE_NAME" == "claude" ]]; then
  ARGS=(-p "$PROMPT")
  [[ $DRY_RUN -eq 0 ]] && ARGS+=(--permission-mode acceptEdits)
else
  ARGS=(-p "$PROMPT" --output-format text)
fi
[[ -n "$MODEL" ]] && ARGS+=(--model "$MODEL")

log "Engine: $ENGINE_NAME at $AGENT"
set +e
"$AGENT" "${ARGS[@]}" 2>&1 | tee -a "$LOG"
CODE=${PIPESTATUS[0]}
set -e

log "Agent exited with code $CODE"

if [[ $CODE -ne 0 ]]; then
  $PYTHON scripts/notify.py --title "CTI doc sync FAILED" \
    --message "The monthly CTI documentation sync exited with code $CODE. Engine: $ENGINE_NAME. Log: $LOG"
fi

exit $CODE
