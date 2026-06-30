# AGENTS.md

## 项目目标

本项目把用户提供的半导体、AI 算力板块截图整理为可离线打开的交互研究网页，面向个人产业研究，不提供荐股、目标价或买卖建议。

成品覆盖：

- 4 条主链：材料与器件、光互连、算力基础设施、算力运营。
- 20 个产业节点、80 个截图公司位置。
- 79 家去重公司；中科曙光同时属于 AI 服务器和液冷。
- 2021–2025 年年度财务与最新 TTM 市盈率。
- A+H 公司合并为同一公司档案，两地代码和估值分别展示。

## 当前状态

- 成品：`dist/中国半导体与AI算力产业链研究.html`
- 数据快照：2026-06-29，Asia/Shanghai。
- 79 家公司均已匹配上市代码并生成财务档案。
- 港股映射：东方电气 `01072.HK`、长飞光纤光缆 `06869.HK`；不为其他节点强行补充港股。
- 2021 年暂无数据：南网数字、摩尔线程、沐曦股份。页面应继续显示“暂无数据”，不得填零或估算。
- 最近校验：20 节点 / 80 位置 / 79 家唯一公司，市场和财务接口无报错。

## 技术配置

- Windows + PowerShell。
- Python 3.12；依赖见 `requirements.txt`，主要为 AKShare 和 pandas。
- Node.js 24 仅用于浏览器冒烟测试。
- 前端为原生 HTML、CSS、JavaScript，无运行时框架或 CDN 依赖。
- `scripts/build.py` 将 CSS、JavaScript 和标准化 JSON 内嵌为单个 HTML，成品无需本地服务器。

## 目录职责

- `截图.jpg`：用户提供的原始参考图，不修改。
- `data/catalog.json`：产业链、节点关系、截图名单、A/H 映射、代码覆盖和分类审计说明；这是业务分类的主要编辑入口。
- `data/research_data.json`：网页使用的标准化数据快照，由脚本生成，不手工维护。
- `data/validation_report.json`：代码匹配、接口异常和缺失年份报告。
- `data/raw/*.json`：每家公司的精简原始字段缓存，用于追踪数据来源与排错。
- `src/index.html`、`src/styles.css`、`src/app.js`：网页源文件。
- `src/schema.d.ts`：`ChainNode`、`Company`、`Listing`、`AnnualFinancial`、`SourceRecord` 等数据类型。
- `scripts/update_data.py`：代码解析、财务/估值抓取、容错回退和标准化。
- `scripts/validate_data.py`：目录及输出数据校验。
- `scripts/build.py`：构建单文件网页。
- `scripts/refresh.ps1`：完整刷新入口。
- `tests/browser_smoke.mjs`：Chrome CDP 交互与 390px 响应式冒烟测试。
- `tests/screenshots/`：桌面和移动端视觉验收截图。

## 数据口径

每家公司每个年度包含：

- 营业收入、营收同比。
- 归母净利润、归母净利润同比。
- 毛利率、ROE。
- 经营活动现金流、资产负债率。
- 各上市地最新 TTM/动态市盈率及快照日期。

规则：

- 年度固定为 2021–2025，只采用 12 月 31 日年度报告记录。
- 金额转换为亿元，保留报告币种；当前主体财务以 CNY 为主。
- 比例保留一位小数。
- 亏损或无有效估值的公司，PE 存为 `null`，页面显示“不适用”。
- 缺失数据存为 `null`，不得写成 `0`。
- 东方财富财务分析提供营收、归母净利、毛利率、ROE、现金流比例和负债率；新浪财务指标作为现金流与负债率的补充来源。
- A 股代码列表和估值采用东方财富定向批量接口，避免扫描全市场行情造成刷新卡顿。
- 接口失败时优先沿用上一次成功快照，并将异常写入校验报告。

## 名单与审计约定

- 保留截图原始映射，即使公司同时属于多个概念。
- `申菱环境`是对截图文字的标准简称校正。
- CPO、OCS、固态变压器、燃气轮机、算电协同等节点包含“概念相关”公司，页面必须保留审计说明，不得暗示其已形成对应业务的规模收入。
- 特殊代码覆盖位于 `catalog.json`：亨通光电 `600487`、优刻得 `688158`、摩尔线程 `688795`、沐曦股份 `688802`。原因是行情简称可能带 `XD`、`-W`、`-U` 等前后缀。
- 港股只在业务与节点直接相关且可核验时加入，不按数量补齐。

## 常用命令

完整更新财务、估值、校验并重新构建：

```powershell
.\scripts\refresh.ps1
```

仅刷新代码与估值，沿用现有财务快照：

```powershell
python scripts/update_data.py --skip-financials
python scripts/validate_data.py
python scripts/build.py
```

只校验和构建：

```powershell
python scripts/validate_data.py
python scripts/build.py
```

浏览器冒烟测试：

```powershell
node tests/browser_smoke.mjs
```

冒烟测试应通过：20 个节点、首屏公司卡、节点筛选、公司详情、六项财务图切换、代码搜索、港股筛选及 390px 无页面横向溢出。

## 修改工作流

1. 修改产业关系或公司名单：编辑 `data/catalog.json`。
2. 修改数据抽取：编辑 `scripts/update_data.py`，保留旧快照回退和 `null` 语义。
3. 修改页面：只编辑 `src/`，不要直接编辑 `dist/`。
4. 运行校验、构建和浏览器冒烟测试。
5. 确认 `data/validation_report.json` 没有新增未解释异常，再交付 `dist/` 成品。

## 视觉约束

- 主题是“浅色硅片 + 铜互连 + 光刻蓝”，避免改成通用深色金融大屏。
- 产业节点像芯片焊盘，四条主链体现真实结构，不用装饰性编号替代信息关系。
- 桌面与移动端都必须可用；产业图在窄屏内允许自身横向滚动，但页面主体不能横向溢出。
- 保持键盘焦点、Escape 关闭详情、`prefers-reduced-motion` 和清晰的空数据状态。

## 维护禁忌

- 不直接修改生成的 `research_data.json` 或 `dist/*.html`。
- 不用模拟值填补财务缺口。
- 不将动态 PE 当成五年历史估值序列。
- 不删除分类争议说明，也不把供应链映射写成已经确认的主营收入。
- 不在联网刷新失败时覆盖上次成功财务快照为空数据。

## 公网发布

- 默认托管目标为 GitHub Pages，工作流位于 `.github/workflows/deploy-pages.yml`。
- `main` 分支推送后完整刷新并发布；工作日 17:20（北京时间）刷新估值；每周日 06:30 完整刷新财务。
- GitHub Actions 发布目录固定为 `dist/`，不要改为直接发布 `src/`。
- 自动任务会将 `data/research_data.json` 与 `data/validation_report.json` 写回 `main`；对应 bot 提交由 `paths-ignore` 避免触发发布循环。
- 本地可运行 `scripts/publish.ps1` 完成刷新、校验、构建、提交和推送。
- 首次上线需要创建 GitHub 仓库、将 Pages Source 设为 GitHub Actions，并把本地 `main` 推送到远程；具体命令见 `README.md`。
