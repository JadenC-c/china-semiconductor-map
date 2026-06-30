# 中国半导体与 AI 算力产业链研究网页

这是一个可离线使用、也可持续发布到公网的单页研究网站。公开版推荐托管在 GitHub Pages：代码或数据推送到 `main` 后自动刷新并发布，工作日更新估值，每周完整刷新年度财务。

## 打开成品

双击 `dist/中国半导体与AI算力产业链研究.html`。全部样式、脚本和数据均已内嵌，不需要本地服务器。

## 更新数据

在 PowerShell 中运行：

```powershell
.\scripts\refresh.ps1
```

更新流程会通过 AKShare 获取 A/H 股代码、2021–2025 年财务指标和最新 TTM 市盈率，保留精简原始缓存，生成校验报告，并重新构建单文件网页。若某家公司接口失败，会优先沿用上一次成功快照并在页面中标注。

仅更新代码和估值、不重新抓取财务时：

```powershell
python scripts/update_data.py --skip-financials
python scripts/build.py
```

## 文件说明

- `data/catalog.json`：产业链、截图公司名单、关系与纠错说明。
- `data/research_data.json`：网页读取的标准化数据快照。
- `data/validation_report.json`：代码匹配、接口失败和缺失年份报告。
- `data/raw/`：每家公司本次抓取所用的精简原始字段缓存。
- `src/`：网页源文件和数据类型定义。
- `scripts/`：更新、校验与单文件构建脚本。

本项目仅用于产业研究与信息整理，不构成投资建议。

## 首次上线

项目已包含 [`.github/workflows/deploy-pages.yml`](.github/workflows/deploy-pages.yml)，使用 GitHub 官方 Pages Actions 构建和发布。首次只需完成一次仓库连接：

1. 在 GitHub 新建一个仓库，例如 `china-semiconductor-map`。公开仓库可使用免费的 GitHub Pages。
2. 在本目录打开 PowerShell，执行：

```powershell
git init -b main
git config user.name "你的 GitHub 昵称"
git config user.email "你的 GitHub 邮箱"
git add --all
git commit -m "首次发布产业链研究网页"
git remote add origin https://github.com/你的用户名/china-semiconductor-map.git
git push -u origin main
```

3. 打开仓库的 `Settings → Pages`，把 `Source` 设为 `GitHub Actions`。
4. 在仓库的 `Actions` 页面等待“更新并发布研究网页”完成。公开地址通常为：

```text
https://你的用户名.github.io/china-semiconductor-map/
```

如果仓库名就是 `你的用户名.github.io`，地址则为 `https://你的用户名.github.io/`。

## 以后如何更新线上内容

编辑 `data/catalog.json` 或 `src/` 后，可以运行一条命令完成数据刷新、校验、构建、提交和推送：

```powershell
.\scripts\publish.ps1 -Mode full -Message "更新产业链分类与公司数据"
```

可选更新方式：

- `full`：重新获取财务和估值，适合新增公司或年度报告更新。
- `valuation`：沿用五年财务，仅更新代码、名称和估值，速度更快。
- `build-only`：不联网，直接用当前数据重新构建页面。

线上自动任务：

- 每个工作日北京时间 17:20 更新上市代码、名称和估值快照。
- 每周日北京时间 06:30 完整刷新五年财务。
- 每次向 `main` 推送内容时完整刷新并重新发布。
- 也可在 GitHub 的 `Actions → 更新并发布研究网页 → Run workflow` 手动选择刷新方式。

发布采用“先校验、后替换”：任何构建或结构校验失败都会中止部署，线上保留上一次成功版本。单家公司接口异常时，数据脚本会沿用该公司的上次成功快照并在校验报告中记录。成功的自动更新会把 `research_data.json` 和校验报告写回 `main`，确保下一次定时刷新从最近成功快照继续，而不是退回旧数据。

## 自定义域名（可选）

GitHub Pages 支持绑定自己的域名。网站先用默认 `github.io` 地址上线即可；购买域名后，再到仓库 `Settings → Pages → Custom domain` 配置，不影响当前数据和更新流程。
