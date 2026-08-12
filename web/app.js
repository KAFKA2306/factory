const $ = (selector) => document.querySelector(selector);
let catalog;

const labels = {
  country_profiles: "国・地域プロファイル",
  factory_records: "工場・製造拠点",
  factory_covered_countries: "工場収録国・地域",
  verified_no_qualifying_factory_countries: "公式非該当地域"
};

function renderMetrics() {
  $("#metrics").innerHTML = Object.entries(labels).map(([key, label]) =>
    `<div class="metric"><strong>${catalog.coverage[key].toLocaleString()}</strong><span>${label}</span></div>`
  ).join("");
}

function setupFilters() {
  const countries = new Map(catalog.countries.map(x => [x.iso2, x.name]));
  const countrySelect = $("#country");
  [...new Set(catalog.facilities.map(x => x.country_code))].sort()
    .forEach(code => countrySelect.add(new Option(`${code} — ${countries.get(code) || code}`, code)));
  const processSelect = $("#process");
  [...new Set(catalog.facilities.flatMap(x => x.processes))].sort()
    .forEach(value => processSelect.add(new Option(value, value)));
  ["country", "process", "query"].forEach(id => $(`#${id}`).addEventListener("input", renderFacilities));
}

function renderFacilities() {
  const country = $("#country").value;
  const process = $("#process").value;
  const query = $("#query").value.trim().toLowerCase();
  const rows = catalog.facilities.filter(row =>
    (!country || row.country_code === country) &&
    (!process || row.processes.includes(process)) &&
    (!query || [row.name, ...row.products, ...row.processes].join(" ").toLowerCase().includes(query))
  );
  $("#count").textContent = `${rows.length}件`;
  const target = $("#facilities");
  target.innerHTML = "";
  const template = $("#facility-template");
  rows.forEach(row => {
    const node = template.content.cloneNode(true);
    node.querySelector(".country").textContent = row.country_code;
    node.querySelector(".status").textContent = row.status;
    node.querySelector("h3").textContent = row.name;
    node.querySelector(".meta").textContent =
      `${row.facility_type} / ${row.granularity}${row.production_start ? ` / 生産開始 ${row.production_start}` : ""}`;
    node.querySelector(".products").textContent = row.products.join("、");
    node.querySelector(".processes").textContent = row.processes.join("、");
    const link = node.querySelector(".source");
    link.href = row.sources[0].url;
    target.appendChild(node);
  });
}


function formatAmount(value, currency, scale = "unit") {
  const multipliers = { unit: 1, thousand: 1e3, million: 1e6, billion: 1e9 };
  const absolute = value * (multipliers[scale] || 1);
  return new Intl.NumberFormat("ja-JP", {
    style: "currency",
    currency,
    notation: "compact",
    maximumFractionDigits: 2
  }).format(absolute);
}

function renderAssets() {
  $("#asset-count").textContent = `${catalog.assets.length}件`;
  $("#assets").innerHTML = catalog.assets.map(row => `
    <article class="card compact-card">
      <div class="card-head"><span>${row.asset_type}</span><span>${row.status}</span></div>
      <h3>${row.name}</h3>
      <p class="meta">${row.facility_id}</p>
      <a class="source" href="${row.sources[0].url}" target="_blank" rel="noreferrer">公式出典</a>
    </article>
  `).join("");
}

function renderInvestments() {
  $("#investment-count").textContent = `${catalog.investments.length}件`;
  $("#investments").innerHTML = catalog.investments.map(row => {
    const impacts = Object.entries(row.expected_impacts || {})
      .map(([key, value]) => `<li><span>${key}</span><strong>${Number(value).toLocaleString()}</strong></li>`)
      .join("");
    return `
      <article class="card compact-card">
        <div class="card-head"><span>${row.announcement_date}</span><span>${row.status}</span></div>
        <h3>${formatAmount(row.amount, row.currency)}</h3>
        <p>${row.purpose.join("、")}</p>
        ${impacts ? `<ul class="fact-list">${impacts}</ul>` : ""}
        <a class="source" href="${row.sources[0].url}" target="_blank" rel="noreferrer">公式出典</a>
      </article>
    `;
  }).join("");
}

function renderFinancials() {
  $("#financial-count").textContent = `${catalog.financials.length}件`;
  const keys = [
    ["total_assets", "総資産"],
    ["total_liabilities", "負債"],
    ["total_shareholders_equity", "株主資本"],
    ["sales_revenues", "営業収益"],
    ["operating_income", "営業利益"],
    ["cash_flow_from_operating_activities", "営業CF"]
  ];
  $("#financials").innerHTML = catalog.financials.map(row => `
    <article class="card financial-card">
      <div class="card-head"><span>${row.fiscal_year}</span><span>${row.accounting_standard}</span></div>
      <h3>${row.company_id}</h3>
      <div class="money-grid">
        ${keys.filter(([key]) => row.metrics[key] !== undefined).map(([key, label]) => `
          <div><span>${label}</span><strong>${formatAmount(row.metrics[key], row.currency, row.scale)}</strong></div>
        `).join("")}
      </div>
      <a class="source" href="${row.sources[0].url}" target="_blank" rel="noreferrer">公式財務資料</a>
    </article>
  `).join("");
}

fetch("catalog.json")
  .then(response => {
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  })
  .then(data => {
    catalog = data;
    renderMetrics();
    setupFilters();
    renderFacilities();
    renderAssets();
    renderInvestments();
    renderFinancials();
  })
  .catch(error => {
    document.body.innerHTML = `<main><h1>FactoryDB</h1><p>データ読み込みに失敗しました: ${error.message}</p></main>`;
  });
