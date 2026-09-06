#!/usr/bin/env bash
# Register the monthly CTI documentation sync with cron, for macOS and Linux.
#
#   ./scripts/register_schedule.sh            install at 07:30
#   ./scripts/register_schedule.sh --at 09:00
#   ./scripts/register_schedule.sh --remove
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AT="07:30"
REMOVE=0
TAG="# genelabs-cti-doc-sync"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --at) AT="$2"; shift 2 ;;
    --remove) REMOVE=1; shift ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

HOUR="${AT%%:*}"
MIN="${AT##*:}"

current="$(crontab -l 2>/dev/null || true)"
cleaned="$(printf '%s\n' "$current" | grep -v -F "$TAG" || true)"

if [[ $REMOVE -eq 1 ]]; then
  printf '%s\n' "$cleaned" | crontab -
  echo "Removed the CTI doc sync cron entry."
  exit 0
fi

# Fire on the 1st, 2nd and 3rd; the date guard runs the work on the first
# weekday only.
entry="${MIN#0} ${HOUR#0} 1,2,3 * * cd $REPO && ./scripts/run_doc_sync.sh >> $REPO/runs/cron.log 2>&1 $TAG"
printf '%s\n%s\n' "$cleaned" "$entry" | grep -v '^$' | crontab -

echo "Installed cron entry:"
echo "  $entry"
