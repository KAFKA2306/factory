const $ = (selector) => document.querySelector(selector);
let catalog;

const MAX_COMPARE = 4;
const selectedFacilityIds = new Set();

const coverageLabels = {
  factory_covered_countries: "工場収録国・地域",
  verified_no_qualifying_factory_countries: "公式非該当",
  coverage_missing_countries: "未確認（unresolved）",
  country_profiles: "対象国・地域"
};

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function company(companyId) {
  return catalog.companies.find(row => row.id === companyId);
}

function companyName(companyId) {
  return company(companyId)?.legal_name || company(companyId)?.name || companyId || "";
}

function facilityById(facilityId) {
  return catalog.facilities.find(row => row.id === facilityId);
}

function firstSource(row) {
  return row?.sources?.[0] || null;
}

function sourceReference(source, label = "公式一次情報") {
  if (!source?.url) return '<span class="missing">出典未収録</span>';
  const observed = source.retrieved_at ? ` · 取得 ${escapeHtml(source.retrieved_at)}` : "";
  return `<a href="${escapeHtml(source.url)}" target="_blank" rel="noreferrer">${escapeHtml(label)}</a><small>${observed}</small>`;
}

function renderHeroStats() {
  const c = catalog.coverage;
  $("#hero-stats").innerHTML = `
    <span><strong>${c.factory_records.toLocaleString()}</strong> 製造拠点</span>
    <span><strong>${c.factory_covered_countries.toLocaleString()}</strong> 国・地域に工場</span>
    <span><strong>${catalog.companies.length.toLocaleString()}</strong> 企業</span>
  `;
}

function renderMetrics() {
  $("#metrics").innerHTML = Object.entries(coverageLabels).map(([key, label]) =>
    `<div class="metric"><strong>${catalog.coverage[key].toLocaleString()}</strong><span>${label}</span></div>`
  ).join("");
  $("#coverage-state").textContent =
    `unresolved ${catalog.coverage.coverage_missing_countries}件 / ` +
    `verified_no_qualifying_factory ${catalog.coverage.verified_no_qualifying_factory_countries}件`;
}

function setSelectValue(id, value) {
  if (!value) return;
  const select = $(`#${id}`);
  if ([...select.options].some(option => option.value === value)) select.value = value;
}

function restoreUrlState() {
  const params = new URLSearchParams(location.search);
  setSelectValue("country", params.get("country"));
  setSelectValue("process", params.get("process"));
  setSelectValue("sort", params.get("sort"));
  $("#query").value = params.get("q") || "";

  const requested = (params.get("compare") || "").split(",").filter(Boolean);
  requested.forEach(id => {
    if (selectedFacilityIds.size < MAX_COMPARE && facilityById(id)) selectedFacilityIds.add(id);
  });
}

function syncUrlState() {
  const params = new URLSearchParams(location.search);
  const values = {
    country: $("#country").value,
    process: $("#process").value,
    q: $("#query").value.trim(),
    sort: $("#sort").value === "country" ? "" : $("#sort").value,
    compare: [...selectedFacilityIds].join(",")
  };
  Object.entries(values).forEach(([key, value]) => {
    if (value) params.set(key, value);
    else params.delete(key);
  });
  const query = params.toString();
  history.replaceState(null, "", `${location.pathname}${query ? `?${query}` : ""}${location.hash}`);
}

function setupFilters() {
  const countries = new Map(catalog.countries.map(row => [row.iso2, row.name]));
  [...new Set(catalog.facilities.map(row => row.country_code))].sort()
    .forEach(code => $("#country").add(new Option(`${code} — ${countries.get(code) || code}`, code)));
  [...new Set(catalog.facilities.flatMap(row => row.processes))].sort()
    .forEach(value => $("#process").add(new Option(value, value)));

  ["country", "process", "query", "sort"].forEach(id => $(`#${id}`).addEventListener("input", () => {
    renderFacilities();
    syncUrlState();
  }));
  $("#clear-query").addEventListener("click", () => {
    $("#query").value = "";
    $("#query").focus();
    renderFacilities();
    syncUrlState();
  });
  $("#clear-comparison").addEventListener("click", () => {
    selectedFacilityIds.clear();
    renderFacilities();
    renderComparison();
    syncUrlState();
  });
}

function toggleComparison(row, button) {
  if (selectedFacilityIds.has(row.id)) {
    selectedFacilityIds.delete(row.id);
  } else if (selectedFacilityIds.size >= MAX_COMPARE) {
    $("#comparison-status").textContent = `比較できるのは最大${MAX_COMPARE}拠点です。1件外してから追加してください。`;
    return;
  } else {
    selectedFacilityIds.add(row.id);
  }
  const selected = selectedFacilityIds.has(row.id);
  button.setAttribute("aria-pressed", String(selected));
  button.textContent = selected ? "比較から外す" : "比較に追加";
  renderComparison();
  syncUrlState();
}

function renderFacilities() {
  const country = $("#country").value;
  const process = $("#process").value;
  const query = $("#query").value.trim().toLowerCase();
  const sort = $("#sort").value;

  const rows = catalog.facilities.filter(row => {
    const haystack = [row.name, companyName(row.company_id), row.country_code, ...row.products, ...row.processes]
      .join(" ").toLowerCase();
    return (!country || row.country_code === country) &&
      (!process || row.processes.includes(process)) &&
      (!query || haystack.includes(query));
  }).sort((a, b) => {
    if (sort === "name") return a.name.localeCompare(b.name);
    return a.country_code.localeCompare(b.country_code) || a.name.localeCompare(b.name);
  });

  $("#count").textContent = `${rows.length.toLocaleString()}件`;
  $("#empty-state").hidden = rows.length !== 0;
  const target = $("#facilities");
  target.innerHTML = "";
  const template = $("#facility-template");

  rows.forEach(row => {
    const node = template.content.cloneNode(true);
    node.querySelector(".country").textContent = row.country_code;
    node.querySelector(".status").textContent = row.status;
    node.querySelector("h3").textContent = row.name;
    node.querySelector(".meta").textContent = `${companyName(row.company_id)} · ${row.facility_type}${row.production_start ? ` · 生産開始 ${row.production_start}` : ""}`;
    node.querySelector(".products").textContent = row.products.join("、");
    node.querySelector(".processes").textContent = row.processes.join("、");
    const compare = node.querySelector(".compare-button");
    const selected = selectedFacilityIds.has(row.id);
    compare.setAttribute("aria-pressed", String(selected));
    compare.textContent = selected ? "比較から外す" : "比較に追加";
    compare.setAttribute("aria-label", `${row.name}を${selected ? "比較から外す" : "比較に追加"}`);
    compare.addEventListener("click", () => toggleComparison(row, compare));
    const link = node.querySelector(".source");
    link.href = firstSource(row)?.url || "#";
    target.appendChild(node);
  });
}

function formatAmount(value, currency, scale = "unit") {
  const multipliers = {unit: 1, thousand: 1e3, million: 1e6, billion: 1e9};
  return new Intl.NumberFormat("ja-JP", {
    style: "currency", currency, notation: "compact", maximumFractionDigits: 2
  }).format(value * (multipliers[scale] || 1));
}

function missingText() {
  return '<span class="missing">未収録（0とは限りません）</span>';
}

function facilityClaim(row, value) {
  const source = firstSource(row);
  return `${escapeHtml(value)}<div class="claim-source">${sourceReference(source)}</div>`;
}

function renderScaleMetrics(row) {
  const entries = Object.entries(row.scale_metrics || {});
  if (!entries.length) return missingText();
  return facilityClaim(row, entries.map(([key, value]) => `${key}: ${value}`).join(" / "));
}

function renderAssets(row) {
  const items = catalog.assets.filter(asset => asset.facility_id === row.id);
  if (!items.length) return missingText();
  return items.map(asset => `
    <div class="comparison-item"><strong>${escapeHtml(asset.name)}</strong><br>
    ${escapeHtml(asset.asset_type)} · ${escapeHtml(asset.status)}
    <div class="claim-source">${sourceReference(firstSource(asset), "設備の出典")}</div></div>
  `).join("");
}

function renderInvestments(row) {
  const items = catalog.investments.filter(investment => (investment.facility_ids || []).includes(row.id));
  if (!items.length) return missingText();
  return items.map(investment => `
    <div class="comparison-item"><strong>${escapeHtml(formatAmount(investment.amount, investment.currency))}</strong><br>
    ${escapeHtml(investment.purpose.join("、"))}
    <div class="claim-source">${sourceReference(firstSource(investment), "投資の出典")}</div></div>
  `).join("");
}

function renderComparison() {
  const rows = [...selectedFacilityIds].map(facilityById).filter(Boolean);
  const empty = $("#comparison-empty");
  const target = $("#comparison-table");
  $("#clear-comparison").hidden = rows.length === 0;
  empty.hidden = rows.length !== 0;
  target.hidden = rows.length === 0;

  if (!rows.length) {
    target.innerHTML = "";
    $("#comparison-status").textContent = "比較する拠点を2件以上選んでください。";
    return;
  }

  $("#comparison-status").textContent = rows.length < 2
    ? "あと1拠点選ぶと比較できます。"
    : `${rows.length}拠点を比較中。URLを共有すると同じ比較状態を復元できます。`;

  const column = (row, html) => `<td>${html}</td>`;
  const facilitySource = row => facilityClaim(row, `${row.country_code} / ${row.status}`);
  const companyCell = row => {
    const item = company(row.company_id);
    return `${escapeHtml(companyName(row.company_id))}<div class="claim-source">${sourceReference(firstSource(item), "企業の出典")}</div>`;
  };

  const bodyRows = [
    ["企業", companyCell],
    ["国・稼働状態", facilitySource],
    ["製品", row => facilityClaim(row, row.products.join("、"))],
    ["工程", row => facilityClaim(row, row.processes.join("、"))],
    ["規模・能力", renderScaleMetrics],
    ["設備", renderAssets],
    ["投資", renderInvestments]
  ];

  target.innerHTML = `<table class="comparison-table">
    <thead><tr><th scope="col">項目</th>${rows.map(row => `<th scope="col">${escapeHtml(row.name)}</th>`).join("")}</tr></thead>
    <tbody>${bodyRows.map(([label, render]) => `<tr><th scope="row">${label}</th>${rows.map(row => column(row, render(row))).join("")}</tr>`).join("")}</tbody>
  </table>`;
}

function renderRelatedData() {
  $("#asset-count").textContent = `${catalog.assets.length}件`;
  $("#assets").innerHTML = catalog.assets.map(row => `
    <article><strong>${escapeHtml(row.name)}</strong><span>${escapeHtml(row.asset_type)} · ${escapeHtml(row.status)}</span>${sourceReference(firstSource(row), "公式出典")}</article>
  `).join("");

  $("#investment-count").textContent = `${catalog.investments.length}件`;
  $("#investments").innerHTML = catalog.investments.map(row => `
    <article><strong>${escapeHtml(formatAmount(row.amount, row.currency))}</strong><span>${escapeHtml(row.purpose.join("、"))}</span>${sourceReference(firstSource(row), "公式出典")}</article>
  `).join("");

  $("#financial-count").textContent = `${catalog.financials.length}件`;
  $("#financials").innerHTML = catalog.financials.map(row => `
    <article><strong>${escapeHtml(companyName(row.company_id))}</strong><span>${escapeHtml(row.fiscal_year)} · ${escapeHtml(row.accounting_standard)}</span>${sourceReference(firstSource(row), "公式財務資料")}</article>
  `).join("");
}

fetch("catalog.json")
  .then(response => {
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  })
  .then(data => {
    catalog = data;
    renderHeroStats();
    renderMetrics();
    setupFilters();
    restoreUrlState();
    renderFacilities();
    renderComparison();
    renderRelatedData();
    $("#page-status").textContent = "データを読み込みました。検索条件と比較対象はURLで共有できます。";
  })
  .catch(error => {
    $("#page-status").className = "status-line error";
    $("#page-status").textContent = `データ読み込みに失敗しました: ${error.message}`;
    $("#empty-state").hidden = false;
    $("#facilities").innerHTML = "";
  });
