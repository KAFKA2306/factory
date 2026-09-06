import {execFileSync} from "node:child_process";

const targetUrl = process.argv[2];
if (!targetUrl) throw new Error("usage: node scripts/daily_dashboard_smoke.mjs <url>");

const chrome = execFileSync(
  "bash",
  ["-lc", "command -v google-chrome || command -v google-chrome-stable || command -v chromium || command -v chromium-browser"],
  {encoding: "utf8"},
).trim();
if (!chrome) throw new Error("Chrome/Chromium is required for the daily dashboard smoke test");

const indexUrl = new URL("api/v1/robotics/index.json", targetUrl);
const recordsUrl = new URL("api/v1/robotics/records.json", targetUrl);
const [indexResponse, recordsResponse] = await Promise.all([
  fetch(indexUrl, {cache: "no-store"}),
  fetch(recordsUrl, {cache: "no-store"}),
]);
if (!indexResponse.ok) throw new Error(`robotics index HTTP ${indexResponse.status}`);
if (!recordsResponse.ok) throw new Error(`robotics records HTTP ${recordsResponse.status}`);

const [index, recordsPayload] = await Promise.all([indexResponse.json(), recordsResponse.json()]);
const records = [...(recordsPayload.records || [])].sort((a, b) =>
  String(b.observed_at || "").localeCompare(String(a.observed_at || "")) ||
  String(b.source_published_at || "").localeCompare(String(a.source_published_at || "")),
);
if (!records.length) throw new Error("robotics records are empty");

const latest = records[0];
const expectedCounts = index.coverage?.status_counts || {};
for (const status of ["operational", "installed", "ordered", "planned"]) {
  if (!Number.isInteger(expectedCounts[status])) throw new Error(`missing ${status} count`);
}

const dom = execFileSync(chrome, [
  "--headless=new",
  "--disable-gpu",
  "--no-sandbox",
  "--disable-dev-shm-usage",
  "--virtual-time-budget=8000",
  "--dump-dom",
  targetUrl,
], {encoding: "utf8", maxBuffer: 16 * 1024 * 1024});

const expectedExplorerHref = `?q=${encodeURIComponent(latest.company)}#explorer`;
const requiredFragments = [
  'id="today"',
  'class="daily-feature"',
  latest.company,
  latest.factory,
  latest.observed_at,
  "この企業の工場を見る",
  expectedExplorerHref,
  "一次情報を見る",
  `${index.coverage.observation_count}件の収録済み公開情報を集計`,
  "世界全体の件数ではありません",
];
for (const fragment of requiredFragments) {
  if (!dom.includes(fragment)) throw new Error(`daily dashboard DOM missing: ${fragment}`);
}
for (const count of Object.values(expectedCounts)) {
  if (!dom.includes(`>${count}</strong>`)) throw new Error(`daily dashboard DOM missing status count: ${count}`);
}
const h1Count = (dom.match(/<h1(?:\s|>)/g) || []).length;
if (h1Count !== 1) throw new Error(`expected exactly one H1, found ${h1Count}`);
const searchIndex = dom.indexOf('id="query"');
const dailyIndex = dom.indexOf('id="today"');
if (searchIndex < 0 || dailyIndex < 0 || searchIndex > dailyIndex) {
  throw new Error("factory search must appear before the latest automation block");
}
if (dom.includes("canonical robotics data unavailable") || dom.includes("最新のrobotics evidenceを表示できません")) {
  throw new Error("daily dashboard rendered its unavailable state");
}

console.log(JSON.stringify({
  target: targetUrl,
  latestVerified: {
    observed_at: latest.observed_at,
    company: latest.company,
    factory: latest.factory,
    status: latest.status,
    source_url: latest.source_url,
    explorer_url: expectedExplorerHref,
  },
  journey: {
    h1_count: h1Count,
    search_before_latest: true,
    latest_to_company_facilities_actions: 1,
  },
  coverage: index.coverage,
  retrieved_at: index.retrieved_at,
}, null, 2));
