#!/usr/bin/env bash
# Pulls the Omni Shield reference sample (Markdown + PDF) from the server to
# wherever this is run. Works from Linux, macOS, WSL, or Git Bash on Windows -
# anything with scp and an OpenSSH client. For native Windows PowerShell, use
# pull_reference_sample.ps1 instead.
#
# Requires Tailscale connected on this machine (same network the server is
# reached through everywhere else in this vault) and an SSH key or password
# for nost@crypton already set up - this script doesn't handle auth itself.
#
# Usage:
#   ./pull_reference_sample.sh                # into ./omni-shield-sample/
#   ./pull_reference_sample.sh /path/to/dir    # into a specific folder
set -euo pipefail

HOST="nost@100.64.2.100"   # crypton, over Tailscale
REMOTE_BASE="/home/nost/AI-OS/AI-OS/10_Projects/QuickTurnaroundGigs"
DEST="${1:-./omni-shield-sample}"

# One entry per file to pull. Add more lines here for future reports/orders -
# same pattern, no need to touch anything else in this script.
FILES=(
  "$REMOTE_BASE/Reference_Sample_Report_Omni_Shield.md"
  "$REMOTE_BASE/_infra/omni-shield-competitor-analysis.pdf"
)

mkdir -p "$DEST"
echo "Pulling ${#FILES[@]} file(s) from $HOST into $DEST/"
for f in "${FILES[@]}"; do
  scp "$HOST:$f" "$DEST/"
done
echo "Done."
ls -la "$DEST"
