const $ = (selector) => document.querySelector(selector);
let catalog;

const labels = {
  country_profiles: "国・地域プロファイル",
  factory_records: "工場・製造拠点",
  factory_covered_countries: "工場収録国",
  factory_missing_countries: "工場未収録国"
};

function renderMetrics() {
  $("#metrics").innerHTML = Object.entries(labels).map(([key, label]) =>
    `<div class="metric"><strong>${catalog.coverage[key].toLocaleString()}</strong><span>${label}</span></div>`
  ).join("");
  const missing = catalog.coverage.factory_missing_countries;
  if (missing > 0) {
    const warning = $("#coverage-warning");
    warning.hidden = false;
    warning.textContent = `厳格リリースゲート未達: 工場レコードが0件の国・地域が ${missing} 件あります。国プロファイル自体は全ISOコードを収録しています。`;
  }
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
  })
  .catch(error => {
    document.body.innerHTML = `<main><h1>FactoryDB</h1><p>データ読み込みに失敗しました: ${error.message}</p></main>`;
  });
