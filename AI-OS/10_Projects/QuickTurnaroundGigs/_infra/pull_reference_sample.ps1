# Pulls the Omni Shield reference sample (Markdown + PDF) from the server to
# wherever this is run. For native Windows PowerShell, using scp.exe from the
# built-in OpenSSH client (C:\WINDOWS\System32\OpenSSH\scp.exe). For
# Linux/macOS/WSL/Git Bash, use pull_reference_sample.sh instead.
#
# Requires Tailscale connected on this machine and an SSH key or password for
# nost@crypton already set up - this script doesn't handle auth itself.
#
# Usage:
#   .\pull_reference_sample.ps1                  # into .\omni-shield-sample\
#   .\pull_reference_sample.ps1 -Dest C:\reports  # into a specific folder

param(
    [string]$Dest = ".\omni-shield-sample"
)

$ErrorActionPreference = "Stop"

$RemoteHost = "nost@100.64.2.100"   # crypton, over Tailscale
$RemoteBase = "/home/nost/AI-OS/AI-OS/10_Projects/QuickTurnaroundGigs"

# One entry per file to pull. Add more lines here for future reports/orders -
# same pattern, no need to touch anything else in this script.
$Files = @(
    "$RemoteBase/Reference_Sample_Report_Omni_Shield.md",
    "$RemoteBase/_infra/omni-shield-competitor-analysis.pdf"
)

New-Item -ItemType Directory -Force -Path $Dest | Out-Null
Write-Host "Pulling $($Files.Count) file(s) from $RemoteHost into $Dest\"

foreach ($f in $Files) {
    scp.exe "${RemoteHost}:$f" $Dest
}

Write-Host "Done."
Get-ChildItem $Dest
