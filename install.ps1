<#
  Claude Parachute - friendly Windows installer.

  Run it one of these ways:
    - Right-click this file -> "Run with PowerShell", OR
    - In a terminal:  powershell -ExecutionPolicy Bypass -File .\install.ps1

  No admin rights needed - it installs just for you.
#>

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Say($text, $color = "Gray") { Write-Host "  $text" -ForegroundColor $color }

Write-Host ""
Say "Claude Parachute - let's get your safety net set up" "Cyan"
Write-Host ""

$py = $null
foreach ($cand in @("python", "py")) {
    if (Get-Command $cand -ErrorAction SilentlyContinue) { $py = $cand; break }
}
if (-not $py) {
    Say "I couldn't find Python on this machine." "Red"
    Say "Grab it from https://www.python.org/downloads/ (tick 'Add Python to PATH')," "Red"
    Say "then run me again. I'll be right here." "Red"
    exit 1
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Say "Heads up: I couldn't find git, and Parachute uses it as the snapshot engine." "Yellow"
    Say "Grab it from https://git-scm.com/download/win, then everything will just work." "Yellow"
    Write-Host ""
}

Say "Found Python. Installing Parachute (just for you, no admin needed)..."

& $py -m pip install --user . | Out-Null
if ($LASTEXITCODE -ne 0) {
    Say "The install hit a snag - the pip output above should say why." "Red"
    exit 1
}
Say "Installed cleanly." "Green"

Write-Host ""
Say "All set - your parachute is packed. A few friendly next steps:" "Green"
Write-Host ""
Say "  1. Arm it in a project:   $py -m claude_parachute init"
Say "  2. Make it automatic:     $py -m claude_parachute install-hooks"
Say "  3. See your snapshots:     $py -m claude_parachute list"
Say "  4. Open the dashboard:    $py -m claude_parachute dashboard"
Write-Host ""
Say "Tip: from this folder you can also just type  .\parachute list  etc." "DarkGray"
Say "Pull the cord anytime with:  $py -m claude_parachute restore <number>" "DarkGray"
Write-Host ""
