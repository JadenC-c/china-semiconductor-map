(() => {
  "use strict";

  const data = window.RESEARCH_DATA;
  if (!data) {
    document.body.innerHTML = '<main class="empty-state">数据未载入，请先运行更新与构建脚本。</main>';
    return;
  }

  const nodeById = new Map(data.nodes.map(node => [node.id, node]));
  const companyByName = new Map(data.companies.map(company => [company.name, company]));
  const state = { selectedNode: "ai-server", query: "", market: "all", limit: 24, openCompany: null, metric: "revenue" };
  const metrics = {
    revenue: { label: "营业收入", unit: "亿元", key: "revenue" },
    netProfit: { label: "归母净利润", unit: "亿元", key: "netProfit" },
    grossMargin: { label: "毛利率", unit: "%", key: "grossMargin" },
    roe: { label: "ROE", unit: "%", key: "roe" },
    operatingCashFlow: { label: "经营现金流", unit: "亿元", key: "operatingCashFlow" },
    debtRatio: { label: "资产负债率", unit: "%", key: "debtRatio" }
  };

  const $ = selector => document.querySelector(selector);
  const esc = value => String(value ?? "").replace(/[&<>'"]/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[char]));
  const display = (value, suffix = "") => value == null ? "—" : `${Number(value).toLocaleString("zh-CN", { maximumFractionDigits: 1 })}${suffix}`;
  const latestRow = company => [...company.financials].reverse().find(row => row.revenue != null) || company.financials[company.financials.length - 1];
  const nodeNames = company => company.nodeIds.map(id => nodeById.get(id)?.name).filter(Boolean);

  function initMeta() {
    const date = data.meta.updatedAt ? new Date(data.meta.updatedAt).toLocaleDateString("zh-CN") : "未知日期";
    $("#updateStamp").textContent = `更新于 ${date}`;
    $("#slotCount").textContent = data.meta.screenshotSlotCount;
    $("#companyCount").textContent = data.meta.uniqueCompanyCount;
    $("#footerDisclaimer").textContent = data.meta.disclaimer;
    $("#sourceLinks").innerHTML = data.sources.map(source => `<a href="${esc(source.url)}" target="_blank" rel="noopener">${esc(source.name)} ↗</a>`).join("");
    $("#nodeFilter").insertAdjacentHTML("beforeend", data.nodes.map(node => `<option value="${esc(node.id)}">${esc(node.name)}</option>`).join(""));
  }

  function renderMap() {
    $("#chainMap").innerHTML = data.chains.map((chain, chainIndex) => {
      const nodes = chain.nodeIds.map(id => nodeById.get(id));
      return `<article class="chain-track">
        <div class="track-label"><small>0${chainIndex + 1} · ${esc(chain.eyebrow)}</small><b>${esc(chain.name)}</b><span>${esc(chain.summary)}</span></div>
        <div class="node-list" style="--count:${nodes.length}">${nodes.map((node, index) => `<button class="map-node ${node.id === state.selectedNode ? "active" : ""}" type="button" data-node="${esc(node.id)}" aria-pressed="${node.id === state.selectedNode}"><small>${String(index + 1).padStart(2, "0")} / ${esc(node.stage)}</small><b>${esc(node.name)}</b></button>`).join("")}</div>
      </article>`;
    }).join("");
    document.querySelectorAll(".map-node").forEach(button => button.addEventListener("click", () => selectNode(button.dataset.node)));
    renderNodeInspector();
  }

  function renderNodeInspector() {
    const node = nodeById.get(state.selectedNode);
    $("#nodeInspector").innerHTML = `<div>
      <span class="inspector-kicker">SELECTED NODE / ${esc(node.chainId.toUpperCase())}</span>
      <h3>${esc(node.name)}</h3><span class="stage-pill">${esc(node.stage)}</span>
      <p>${esc(node.description)}</p>
      <div class="inspector-companies">${node.companies.map(name => `<button type="button" data-company="${esc(name)}">${esc(name)}</button>`).join("")}</div>
      ${node.auditNote ? `<div class="audit-box"><b>分类审计</b><br>${esc(node.auditNote)}</div>` : ""}
    </div><dl class="node-facts">
      <div><dt>上游输入</dt><dd>${esc(node.upstream)}</dd></div>
      <div><dt>核心产品</dt><dd>${esc(node.coreProducts)}</dd></div>
      <div><dt>下游去向</dt><dd>${esc(node.downstream)}</dd></div>
      <div><dt>价值观察</dt><dd>${esc(node.valuePosition)}</dd></div>
    </dl>`;
    $("#nodeInspector").querySelectorAll("[data-company]").forEach(button => button.addEventListener("click", () => openCompany(button.dataset.company)));
  }

  function selectNode(nodeId, options = {}) {
    state.selectedNode = nodeId;
    state.limit = 24;
    renderMap();
    $("#nodeFilter").value = nodeId;
    renderCompanies();
    if (options.scroll) $("#map").scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function filteredCompanies() {
    const nodeFilter = $("#nodeFilter").value;
    const query = state.query.trim().toLowerCase();
    return data.companies.filter(company => {
      const matchesNode = nodeFilter === "all" || company.nodeIds.includes(nodeFilter);
      const matchesMarket = state.market === "all" || company.listings.some(listing => listing.market === state.market);
      const haystack = [company.name, ...company.listings.map(listing => listing.code), ...nodeNames(company)].join(" ").toLowerCase();
      return matchesNode && matchesMarket && (!query || haystack.includes(query));
    });
  }

  function cardHtml(company) {
    const latest = latestRow(company) || {};
    const pe = company.listings.find(listing => listing.peTtm != null)?.peTtm;
    return `<button class="company-card" type="button" data-company="${esc(company.name)}">
      <span class="card-listings">${company.listings.length ? company.listings.map(listing => `<span class="market-tag ${listing.market.toLowerCase()}">${esc(listing.market)} · ${esc(listing.code)}</span>`).join("") : '<span class="market-tag">未匹配上市代码</span>'}</span>
      <h3>${esc(company.name)}</h3>
      <span class="node-tags">${nodeNames(company).map(name => `<span>${esc(name)}</span>`).join("")}</span>
      <span class="card-metrics"><span>2025 营收<b>${display(latest.revenue, latest.revenue == null ? "" : " 亿")}</b></span><span>最新 TTM PE<b>${display(pe, pe == null ? "" : "×")}</b></span></span>
      ${company.auditNotes.length ? '<span class="audit-flag">含审计说明</span>' : ""}<i class="status-dot ${esc(company.status)}" title="${esc(company.status)}"></i>
    </button>`;
  }

  function renderCompanies() {
    const filtered = filteredCompanies();
    const visible = filtered.slice(0, state.limit);
    $("#companyGrid").innerHTML = visible.length ? visible.map(cardHtml).join("") : '<div class="empty-state"><b>没有匹配结果</b><br>试试清除市场或产业节点筛选。</div>';
    $("#resultCount").textContent = `显示 ${visible.length} / ${filtered.length} 家`;
    const nodeValue = $("#nodeFilter").value;
    $("#activeFilterText").textContent = nodeValue === "all" ? "全部产业节点" : nodeById.get(nodeValue)?.name || "全部产业节点";
    $("#loadMore").hidden = visible.length >= filtered.length;
    $("#companyGrid").querySelectorAll("[data-company]").forEach(button => button.addEventListener("click", () => openCompany(button.dataset.company)));
  }

  function listingsHtml(company) {
    if (!company.listings.length) return '<span class="market-tag">截图主体 · 未匹配独立上市代码</span>';
    return company.listings.map(listing => `<span class="market-tag ${listing.market.toLowerCase()}">${esc(listing.market)} 股 · ${esc(listing.code)} · PE ${listing.peTtm == null ? "不适用" : `${display(listing.peTtm)}×`}</span>`).join("");
  }

  function companySourceLinks(company) {
    const links = [];
    company.listings.forEach(listing => {
      if (listing.market === "A") {
        const prefix = listing.exchange === "SSE" ? "SH" : "SZ";
        links.push(`<a href="https://emweb.securities.eastmoney.com/pc_hsf10/pages/index.html?type=web&code=${prefix}${esc(listing.code)}#/cwfx" target="_blank" rel="noopener">东方财富财务页 · ${esc(listing.code)} ↗</a>`);
        links.push(`<a href="https://www.cninfo.com.cn/new/fulltextSearch?notautosubmit=&keyWord=${encodeURIComponent(company.name)}" target="_blank" rel="noopener">巨潮公告核验 ↗</a>`);
      } else {
        links.push(`<a href="https://emweb.securities.eastmoney.com/PC_HKF10/NewFinancialAnalysis/index?type=web&code=${esc(listing.code)}" target="_blank" rel="noopener">港股财务页 · ${esc(listing.code)} ↗</a>`);
        links.push('<a href="https://www1.hkexnews.hk/index_c.htm" target="_blank" rel="noopener">港交所披露易 ↗</a>');
      }
    });
    return [...new Set(links)].join("");
  }

  function chartSvg(company, metricKey) {
    const metric = metrics[metricKey];
    const points = company.financials.map(row => ({ year: row.year, value: row[metric.key] }));
    const valid = points.filter(point => point.value != null);
    if (!valid.length) return '<div class="empty-state">该指标暂无可用年度数据。</div>';
    const values = valid.map(point => point.value);
    let min = Math.min(...values), max = Math.max(...values);
    if (min === max) { min -= 1; max += 1; }
    const pad = (max - min) * .18;
    min = Math.min(0, min - pad); max += pad;
    const x = index => 68 + index * 142;
    const y = value => 220 - ((value - min) / (max - min)) * 170;
    const horizontal = [0, .25, .5, .75, 1].map(step => {
      const value = max - (max - min) * step;
      const py = 50 + step * 170;
      return `<line class="grid" x1="55" y1="${py}" x2="660" y2="${py}"/><text x="48" y="${py + 3}" text-anchor="end">${display(value)}</text>`;
    }).join("");
    const segments = [];
    points.forEach((point, index) => {
      const next = points[index + 1];
      if (next && point.value != null && next.value != null) segments.push(`<path class="line" d="M${x(index)} ${y(point.value)}L${x(index + 1)} ${y(next.value)}"/>`);
    });
    const dots = points.map((point, index) => point.value == null
      ? `<text x="${x(index)}" y="150" text-anchor="middle">暂无</text>`
      : `<circle class="point" cx="${x(index)}" cy="${y(point.value)}" r="5"/><text class="value" x="${x(index)}" y="${Math.max(20, y(point.value) - 14)}" text-anchor="middle">${display(point.value)}</text>`).join("");
    const years = points.map((point, index) => `<text x="${x(index)}" y="247" text-anchor="middle">${point.year}</text>`).join("");
    const zeroY = min < 0 && max > 0 ? `<line class="zero" x1="55" y1="${y(0)}" x2="660" y2="${y(0)}"/>` : "";
    return `<svg class="financial-chart" viewBox="0 0 720 260" role="img" aria-label="${esc(company.name)} ${esc(metric.label)} 2021 至 2025 年趋势">${horizontal}${zeroY}${segments.join("")}${dots}${years}<text x="665" y="32" text-anchor="end">单位：${esc(metric.unit)}</text></svg>`;
  }

  function tableHtml(company) {
    return `<div class="data-table-wrap"><table class="data-table"><thead><tr><th>年度</th><th>营收/亿</th><th>同比</th><th>归母净利/亿</th><th>同比</th><th>毛利率</th><th>ROE</th><th>经营现金流/亿</th><th>负债率</th></tr></thead><tbody>${company.financials.map(row => `<tr><td>${row.year}</td><td>${display(row.revenue)}</td><td>${display(row.revenueYoY, row.revenueYoY == null ? "" : "%")}</td><td>${display(row.netProfit)}</td><td>${display(row.netProfitYoY, row.netProfitYoY == null ? "" : "%")}</td><td>${display(row.grossMargin, row.grossMargin == null ? "" : "%")}</td><td>${display(row.roe, row.roe == null ? "" : "%")}</td><td>${display(row.operatingCashFlow)}</td><td>${display(row.debtRatio, row.debtRatio == null ? "" : "%")}</td></tr>`).join("")}</tbody></table></div>`;
  }

  function drawerHtml(company) {
    const latest = latestRow(company) || {};
    const pe = company.listings.find(listing => listing.peTtm != null)?.peTtm;
    return `<div class="drawer-content-inner">
      <span class="drawer-eyebrow">COMPANY PROFILE / ${esc(company.status.toUpperCase())}</span>
      <div class="drawer-title-row"><h2 id="drawerTitle">${esc(company.name)}</h2><div class="drawer-listings">${listingsHtml(company)}</div></div>
      <p class="drawer-nodes">产业映射：${company.nodeIds.map(id => `<button type="button" data-jump-node="${esc(id)}">${esc(nodeById.get(id)?.name)}</button>`).join("")}</p>
      ${company.auditNotes.length ? `<div class="audit-panel"><b>分类与数据审计</b><ul>${company.auditNotes.map(note => `<li>${esc(note)}</li>`).join("")}</ul></div>` : ""}
      <div class="kpi-grid">
        <div class="kpi"><span>${latest.year || 2025} 营业收入</span><b>${display(latest.revenue)}</b><small>亿元 · ${esc(latest.currency || "CNY")}</small></div>
        <div class="kpi"><span>${latest.year || 2025} 归母净利润</span><b>${display(latest.netProfit)}</b><small>亿元 · ${esc(latest.currency || "CNY")}</small></div>
        <div class="kpi"><span>${latest.year || 2025} 毛利率</span><b>${display(latest.grossMargin, latest.grossMargin == null ? "" : "%")}</b><small>年度报告口径</small></div>
        <div class="kpi"><span>最新 TTM PE</span><b>${display(pe, pe == null ? "" : "×")}</b><small>${company.listings[0]?.peAsOf || "暂无快照"}</small></div>
      </div>
      <section class="chart-block"><div class="chart-head"><div><span class="drawer-eyebrow">FIVE-YEAR TREND</span><h3>${esc(metrics[state.metric].label)}</h3></div><div class="metric-tabs">${Object.entries(metrics).map(([key, metric]) => `<button type="button" class="${key === state.metric ? "active" : ""}" data-metric="${key}">${esc(metric.label)}</button>`).join("")}</div></div><div id="chartMount">${chartSvg(company, state.metric)}</div>${tableHtml(company)}</section>
      <div class="source-actions">${companySourceLinks(company) || '<span class="market-tag">未匹配上市主体，暂无公司财务链接</span>'}</div>
    </div>`;
  }

  function openCompany(name) {
    const company = companyByName.get(name);
    if (!company) return;
    state.openCompany = name; state.metric = "revenue";
    $("#drawerContent").innerHTML = drawerHtml(company);
    $("#drawerBackdrop").hidden = false;
    requestAnimationFrame(() => { $("#drawerBackdrop").classList.add("open"); $("#companyDrawer").classList.add("open"); });
    $("#companyDrawer").setAttribute("aria-hidden", "false");
    document.body.classList.add("drawer-open");
    bindDrawerInternal(company);
    $("#closeDrawer").focus();
  }

  function bindDrawerInternal(company) {
    $("#companyDrawer").querySelectorAll("[data-metric]").forEach(button => button.addEventListener("click", () => {
      state.metric = button.dataset.metric;
      $("#drawerContent").innerHTML = drawerHtml(company);
      bindDrawerInternal(company);
    }));
    $("#companyDrawer").querySelectorAll("[data-jump-node]").forEach(button => button.addEventListener("click", () => {
      closeDrawer(); selectNode(button.dataset.jumpNode, { scroll: true });
    }));
  }

  function closeDrawer() {
    $("#companyDrawer").classList.remove("open"); $("#drawerBackdrop").classList.remove("open");
    $("#companyDrawer").setAttribute("aria-hidden", "true"); document.body.classList.remove("drawer-open");
    setTimeout(() => { $("#drawerBackdrop").hidden = true; }, 260); state.openCompany = null;
  }

  function bindEvents() {
    $("#companySearch").addEventListener("input", event => { state.query = event.target.value; state.limit = 24; renderCompanies(); });
    $("#nodeFilter").addEventListener("change", event => { if (event.target.value !== "all") state.selectedNode = event.target.value; state.limit = 24; renderMap(); renderCompanies(); });
    document.querySelectorAll("[data-market]").forEach(button => button.addEventListener("click", () => {
      state.market = button.dataset.market; document.querySelectorAll("[data-market]").forEach(item => item.classList.toggle("active", item === button)); state.limit = 24; renderCompanies();
    }));
    $("#clearFilters").addEventListener("click", clearFilters);
    $("#loadMore").addEventListener("click", () => { state.limit += 24; renderCompanies(); });
    $("#headerSearch").addEventListener("click", () => { $("#companies").scrollIntoView({ behavior: "smooth" }); setTimeout(() => $("#companySearch").focus(), 450); });
    $("#methodButton").addEventListener("click", () => $("#method").scrollIntoView({ behavior: "smooth" }));
    $("#closeDrawer").addEventListener("click", closeDrawer); $("#drawerBackdrop").addEventListener("click", closeDrawer);
    document.addEventListener("keydown", event => { if (event.key === "Escape" && state.openCompany) closeDrawer(); });
  }

  function clearFilters() {
    state.query = ""; state.market = "all"; state.limit = 24; $("#companySearch").value = ""; $("#nodeFilter").value = "all";
    document.querySelectorAll("[data-market]").forEach(button => button.classList.toggle("active", button.dataset.market === "all")); renderCompanies();
  }

  initMeta(); renderMap(); renderCompanies(); bindEvents();
})();
