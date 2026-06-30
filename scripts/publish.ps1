param(
    [ValidateSet("full", "valuation", "build-only")]
    [string]$Mode = "full",
    [string]$Message = "更新产业链研究网页"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Test-Path ".git")) {
    throw '当前目录尚未连接 Git 仓库。请先按照 README 的「首次上线」完成仓库连接。'
}

switch ($Mode) {
    "full" {
        python scripts/update_data.py
        if ($LASTEXITCODE -ne 0) { throw "完整数据刷新失败。" }
    }
    "valuation" {
        python scripts/update_data.py --skip-financials
        if ($LASTEXITCODE -ne 0) { throw "估值刷新失败。" }
    }
    "build-only" {
        Write-Host "使用当前 data/research_data.json 构建。"
    }
}

python scripts/validate_data.py
if ($LASTEXITCODE -ne 0) { throw "数据校验失败，未发布。" }
python scripts/build.py
if ($LASTEXITCODE -ne 0) { throw "网页构建失败，未发布。" }

git add --all
git diff --cached --quiet
if ($LASTEXITCODE -eq 0) {
    Write-Host "没有需要提交的变化；线上版本无需更新。"
    exit 0
}

git commit -m $Message
if ($LASTEXITCODE -ne 0) { throw "Git 提交失败。" }
git push
if ($LASTEXITCODE -ne 0) { throw "Git 推送失败。" }

Write-Host "推送完成。GitHub Actions 将校验、构建并更新公开网页。"
