# Pulls everything needed to publish Micro-SaaS Moat Blueprint on Gumroad,
# from the server to wherever this is run. Same pattern as
# 10_Projects/QuickTurnaroundGigs/_infra/pull_reference_sample.ps1 - see that
# file's comments for auth/host-key notes, unchanged here.
#
# For Linux/macOS/WSL/Git Bash, use pull_moat_blueprint_launch_kit.sh instead.
#
# Usage:
#   .\pull_moat_blueprint_launch_kit.ps1                     # into .\moat-blueprint-launch\
#   .\pull_moat_blueprint_launch_kit.ps1 -Dest C:\launch      # into a specific folder

param(
    [string]$Dest = ".\moat-blueprint-launch"
)

$ErrorActionPreference = "Stop"

$RemoteHost = "nost@100.64.2.100"   # crypton, over Tailscale
$RemoteDir  = "/home/nost/AI-OS/AI-OS/10_Projects/TemplateSales/Micro-SaaS-Moat-Blueprint"

# Everything the Gumroad listing checklist actually needs. cover.png is
# rendered server-side (rsvg-convert) - no more manual screenshot step.
$Files = @(
    "gumroad-listing-copy.md",    # paste into Gumroad: title, tagline, description, FAQ, tags
    "cover.png",                  # upload as the product cover image
    "prompt-pack.pdf",            # attach as a purchasable file
    "example-run-through.md",     # attach as a purchasable file
    "LICENSE.md",                 # attach as a purchasable file
    "notion-template-link.md"     # attach as a purchasable file - NEVER paste this link into
                                   # the public description. Description is visible to anyone
                                   # browsing Gumroad; the Notion page allows duplication, so
                                   # a public link gives the whole product away for free.
)

New-Item -ItemType Directory -Force -Path $Dest | Out-Null
Write-Host "Pulling $($Files.Count) file(s) from $RemoteHost into $Dest\"

foreach ($f in $Files) {
    scp.exe "${RemoteHost}:${RemoteDir}/$f" $Dest
}

Write-Host "Done."
Get-ChildItem $Dest
