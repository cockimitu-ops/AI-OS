# Pulls everything needed to publish The Pricing Teardown on Gumroad, from
# the server to wherever this is run. Same pattern as
# pull_moat_blueprint_launch_kit.ps1 - see that file's comments for auth/
# host-key notes, unchanged here.
#
# Scheduled for Week 3-4 per _infra/LAUNCH-ORDER.md - do not publish this
# before Micro-SaaS Moat Blueprint's Reddit cycle finishes. One product at a
# time, on purpose.
#
# For Linux/macOS/WSL/Git Bash, use pull_pricing_teardown_launch_kit.sh instead.
#
# Usage:
#   .\pull_pricing_teardown_launch_kit.ps1                    # into .\pricing-teardown-launch\
#   .\pull_pricing_teardown_launch_kit.ps1 -Dest C:\launch    # into a specific folder

param(
    [string]$Dest = ".\pricing-teardown-launch"
)

$ErrorActionPreference = "Stop"

$RemoteHost = "nost@100.64.2.100"   # crypton, over Tailscale
$RemoteDir  = "/home/nost/AI-OS/AI-OS/10_Projects/TemplateSales/Pricing-Teardown"

# Everything the Gumroad listing checklist needs. cover.png is rendered
# server-side (rsvg-convert). No notion-template-link.md yet - gets created
# and gated behind purchase once the Notion page actually exists, not before.
$Files = @(
    "gumroad-listing-copy.md",    # paste into Gumroad: title, tagline, description, FAQ, tags
    "cover.png",                  # upload as the product cover image
    "prompt-pack.pdf",            # attach as a purchasable file
    "example-run-through.md",     # attach as a purchasable file
    "LICENSE.md"                  # attach as a purchasable file
)

New-Item -ItemType Directory -Force -Path $Dest | Out-Null
Write-Host "Pulling $($Files.Count) file(s) from $RemoteHost into $Dest\"

foreach ($f in $Files) {
    scp.exe "${RemoteHost}:${RemoteDir}/$f" $Dest
}

Write-Host "Done."
Get-ChildItem $Dest
