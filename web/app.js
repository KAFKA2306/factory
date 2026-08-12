const $ = (selector) => document.querySelector(selector);
let catalog;

const coverageLabels = {
  factory_covered_countries: "工場収録国・地域",
  verified_no_qualifying_factory_countries: "公式非該当",
  country_profiles: "対象国・地域"
};

function companyName(companyId) {
  const row = catalog.companies.find(x => x.id === companyId);
  return row?.name || companyId || "";
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
}

function setupFilters() {
  const countries = new Map(catalog.countries.map(x => [x.iso2, x.name]));
  [...new Set(catalog.facilities.map(x => x.country_code))].sort()
    .forEach(code => $("#country").add(new Option(`${code} — ${countries.get(code) || code}`, code)));
  [...new Set(catalog.facilities.flatMap(x => x.processes))].sort()
    .forEach(value => $("#process").add(new Option(value, value)));

  ["country", "process", "query", "sort"].forEach(id => $(`#${id}`).addEventListener("input", renderFacilities));
  $("#clear-query").addEventListener("click", () => {
    $("#query").value = "";
    $("#query").focus();
    renderFacilities();
  });
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
    const link = node.querySelector(".source");
    link.href = row.sources[0].url;
    target.appendChild(node);
  });
}

function formatAmount(value, currency, scale = "unit") {
  const multipliers = { unit: 1, thousand: 1e3, million: 1e6, billion: 1e9 };
  return new Intl.NumberFormat("ja-JP", {
    style: "currency", currency, notation: "compact", maximumFractionDigits: 2
  }).format(value * (multipliers[scale] || 1));
}

function renderRelatedData() {
  $("#asset-count").textContent = `${catalog.assets.length}件`;
  $("#assets").innerHTML = catalog.assets.map(row => `
    <article><strong>${row.name}</strong><span>${row.asset_type} · ${row.status}</span><a href="${row.sources[0].url}" target="_blank" rel="noreferrer">公式出典</a></article>
  `).join("");

  $("#investment-count").textContent = `${catalog.investments.length}件`;
  $("#investments").innerHTML = catalog.investments.map(row => `
    <article><strong>${formatAmount(row.amount, row.currency)}</strong><span>${row.purpose.join("、")}</span><a href="${row.sources[0].url}" target="_blank" rel="noreferrer">公式出典</a></article>
  `).join("");

  $("#financial-count").textContent = `${catalog.financials.length}件`;
  $("#financials").innerHTML = catalog.financials.map(row => `
    <article><strong>${companyName(row.company_id)}</strong><span>${row.fiscal_year} · ${row.accounting_standard}</span><a href="${row.sources[0].url}" target="_blank" rel="noreferrer">公式財務資料</a></article>
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
    renderFacilities();
    renderRelatedData();
  })
  .catch(error => {
    document.body.innerHTML = `<main><h1>FactoryDB</h1><p>データ読み込みに失敗しました: ${error.message}</p></main>`;
  });
