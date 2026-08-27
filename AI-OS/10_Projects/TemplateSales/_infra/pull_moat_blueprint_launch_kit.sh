#!/usr/bin/env bash
# Pulls everything needed to publish Micro-SaaS Moat Blueprint on Gumroad,
# from the server to wherever this is run. Same pattern as
# 10_Projects/QuickTurnaroundGigs/_infra/pull_reference_sample.sh - see that
# file's comments for auth/host-key notes, unchanged here.
#
# For native Windows PowerShell, use pull_moat_blueprint_launch_kit.ps1 instead.
#
# Usage:
#   ./pull_moat_blueprint_launch_kit.sh                # into ./moat-blueprint-launch/
#   ./pull_moat_blueprint_launch_kit.sh /path/to/dir    # into a specific folder
set -euo pipefail

HOST="nost@100.64.2.100"   # crypton, over Tailscale
REMOTE_DIR="/home/nost/AI-OS/AI-OS/10_Projects/TemplateSales/Micro-SaaS-Moat-Blueprint"
DEST="${1:-./moat-blueprint-launch}"

# Everything the Gumroad listing checklist actually needs. cover.png is
# rendered server-side (rsvg-convert) - no more manual screenshot step.
FILES=(
  "gumroad-listing-copy.md"    # paste into Gumroad: title, tagline, description, FAQ, tags
  "cover.png"                  # upload as the product cover image
  "prompt-pack.pdf"            # attach as a purchasable file
  "example-run-through.md"     # attach as a purchasable file
  "LICENSE.md"                 # attach as a purchasable file
  "notion-template-link.md"    # attach as a purchasable file - NEVER paste this link into
                                # the public description. Description is visible to anyone
                                # browsing Gumroad; the Notion page allows duplication, so
                                # a public link gives the whole product away for free.
)

mkdir -p "$DEST"
echo "Pulling ${#FILES[@]} file(s) from $HOST into $DEST/"
for f in "${FILES[@]}"; do
  scp "$HOST:$REMOTE_DIR/$f" "$DEST/"
done
echo "Done."
ls -la "$DEST"
