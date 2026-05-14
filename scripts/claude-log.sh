#!/usr/bin/env bash
# Append a progress entry to claude-log/ and commit+push to the current branch.
# Usage: scripts/claude-log.sh "titulo curto" "corpo do update" [--status in_progress|completed|blocked]

set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "usage: $0 <title> <body> [--status STATUS]" >&2
  exit 1
fi

title=$1
body=$2
status=in_progress
shift 2
while [[ $# -gt 0 ]]; do
  case $1 in
    --status) status=$2; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 1 ;;
  esac
done

repo_root=$(git rev-parse --show-toplevel)
log_dir="$repo_root/claude-log"
mkdir -p "$log_dir"

ts_file=$(date -u +%Y-%m-%d-%H%M%S)
ts_iso=$(date -u +%Y-%m-%dT%H:%M:%SZ)
slug=$(echo "$title" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-' | sed 's/^-//;s/-$//' | cut -c1-40)
file="$log_dir/${ts_file}-${slug}.md"

session_id=${CLAUDE_SESSION_ID:-${CLAUDE_CODE_SESSION_ID:-unknown}}

cat > "$file" <<EOF
---
session: $session_id
agent: claude
ts: $ts_iso
status: $status
---

# $title

$body
EOF

cd "$repo_root"
git add "$file"
git commit -m "claude-log: $title" >/dev/null
git push -u origin "$(git rev-parse --abbrev-ref HEAD)"

echo "logged: $file"
