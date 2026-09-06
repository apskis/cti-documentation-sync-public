#!/usr/bin/env bash
# Load config/bedrock.env into the current shell.
#
#   source scripts/load_bedrock_env.sh
#
# Must be sourced, not executed: a child process cannot set your environment.
# Existing variables are not overwritten, so an SSO session you already have
# beats the file.

_cti_repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
_cti_env="$_cti_repo/config/bedrock.env"

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  echo "This script must be sourced:  source scripts/load_bedrock_env.sh" >&2
  exit 2
fi

if [[ ! -f "$_cti_env" ]]; then
  echo "config/bedrock.env not found. Copy config/bedrock.env.example to it." >&2
else
  _cti_n=0
  while IFS= read -r _line || [[ -n "$_line" ]]; do
    _line="${_line%%$'\r'}"
    [[ -z "$_line" || "$_line" == \#* || "$_line" != *=* ]] && continue
    _k="${_line%%=*}"; _v="${_line#*=}"
    _k="$(echo "$_k" | tr -d '[:space:]')"
    _v="${_v#\"}"; _v="${_v%\"}"; _v="${_v#\'}"; _v="${_v%\'}"
    [[ -z "$_v" ]] && continue
    if [[ -z "${!_k:-}" ]]; then export "$_k=$_v"; _cti_n=$((_cti_n+1)); fi
  done < "$_cti_env"
  echo "Loaded $_cti_n variable(s) from config/bedrock.env"
  echo "  CLAUDE_CODE_USE_BEDROCK=${CLAUDE_CODE_USE_BEDROCK:-unset}"
  echo "  AWS_REGION=${AWS_REGION:-unset}"
  echo "  ANTHROPIC_MODEL=${ANTHROPIC_MODEL:-unset}"
  unset _line _k _v _cti_n
fi
unset _cti_repo _cti_env
