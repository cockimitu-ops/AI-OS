#!/usr/bin/env bash
# Pulls everything needed to publish The Pricing Teardown on Gumroad, from the
# server to wherever this is run. Same pattern as
# pull_moat_blueprint_launch_kit.sh - see that file's comments for auth/
# host-key notes, unchanged here.
#
# Scheduled for Week 3-4 per _infra/LAUNCH-ORDER.md - do not publish this
# before Micro-SaaS Moat Blueprint's Reddit cycle finishes. One product at a
# time, on purpose: each Reddit post burns a sub's goodwill for a while, and
# spacing keeps three channels alive instead of exhausting one.
#
# For native Windows PowerShell, use pull_pricing_teardown_launch_kit.ps1 instead.
#
# Usage:
#   ./pull_pricing_teardown_launch_kit.sh                # into ./pricing-teardown-launch/
#   ./pull_pricing_teardown_launch_kit.sh /path/to/dir    # into a specific folder
set -euo pipefail

HOST="nost@100.64.2.100"   # crypton, over Tailscale
REMOTE_DIR="/home/nost/AI-OS/AI-OS/10_Projects/TemplateSales/Pricing-Teardown"
DEST="${1:-./pricing-teardown-launch}"

# Everything the Gumroad listing checklist needs. cover.png is rendered
# server-side (rsvg-convert). No notion-template-link.md yet - that file gets
# created (and gated behind purchase, never in the public description - see
# Micro-SaaS Moat Blueprint's launch history) once the Notion page actually
# exists, not before.
FILES=(
  "gumroad-listing-copy.md"    # paste into Gumroad: title, tagline, description, FAQ, tags
  "cover.png"                  # upload as the product cover image
  "prompt-pack.pdf"            # attach as a purchasable file
  "example-run-through.md"     # attach as a purchasable file
  "LICENSE.md"                 # attach as a purchasable file
)

mkdir -p "$DEST"
echo "Pulling ${#FILES[@]} file(s) from $HOST into $DEST/"
for f in "${FILES[@]}"; do
  scp "$HOST:$REMOTE_DIR/$f" "$DEST/"
done
echo "Done."
ls -la "$DEST"
