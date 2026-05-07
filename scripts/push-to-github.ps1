# 推送 AICC-Lite 到 GitHub - 多种方案 (PowerShell)
# 在 PowerShell 中执行: .\scripts\push-to-github.ps1

$ErrorActionPreference = "Stop"
Set-Location "E:\C Project\AICC_Lite"

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "AICC-Lite GitHub Push Helper" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Repo: https://github.com/lucassu2012/aicc-lite" -ForegroundColor Yellow
Write-Host ""

# Method 1: PAT
Write-Host "[Method 1] Personal Access Token (recommended):" -ForegroundColor Green
Write-Host "  1. Visit: https://github.com/settings/tokens/new"
Write-Host "  2. Name: AICC-Lite-deploy"
Write-Host "  3. Scopes: repo, workflow"
Write-Host "  4. Click 'Generate token' and copy"
Write-Host "  5. Run: git push https://lucassu2012:<TOKEN>@github.com/lucassu2012/aicc-lite.git main"
Write-Host ""

# Method 2: GitHub Desktop
Write-Host "[Method 2] GitHub Desktop (one-click GUI):" -ForegroundColor Green
Write-Host "  1. Open GitHub Desktop"
Write-Host "  2. File -> Add local repository -> select 'E:\C Project\AICC_Lite'"
Write-Host "  3. Click 'Publish repository'"
Write-Host ""

# Method 3: gh CLI
Write-Host "[Method 3] Install GitHub CLI:" -ForegroundColor Green
Write-Host "  winget install GitHub.cli"
Write-Host "  gh auth login"
Write-Host "  gh repo create lucassu2012/aicc-lite --source=. --remote=origin --push --public"
Write-Host ""

# Auto: Try git push (will pop credential dialog)
$resp = Read-Host "Press 'Y' to try `git push` now (will trigger credential popup)"
if ($resp -eq "Y" -or $resp -eq "y") {
    Write-Host "Pushing... (a credential popup may appear)" -ForegroundColor Yellow
    git push -u origin main
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Push successful!" -ForegroundColor Green
        Write-Host "Visit: https://github.com/lucassu2012/aicc-lite" -ForegroundColor Cyan
    } else {
        Write-Host "Push failed. Try one of the methods above." -ForegroundColor Red
    }
}
