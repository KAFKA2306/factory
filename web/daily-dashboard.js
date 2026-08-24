const statusLabel = {
  operational: "実運用",
  installed: "導入済み",
  ordered: "発注済み",
  planned: "計画",
};

const statusOrder = ["operational", "installed", "ordered", "planned"];

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatDate(value) {
  if (!value) return "日付不明";
  const date = new Date(`${value}T00:00:00Z`);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("ja-JP", {
    year: "numeric",
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  }).format(date);
}

function formatTimestamp(value) {
  if (!value) return "取得時刻不明";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("ja-JP", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "UTC",
    timeZoneName: "short",
  }).format(date);
}

function humanize(value) {
  return String(value ?? "").replaceAll("_", " ");
}

function injectDashboard() {
  const main = document.querySelector("main");
  const explorer = document.querySelector("#explorer");
  if (!main || !explorer || document.querySelector("#today")) return;

  const section = document.createElement("section");
  section.id = "today";
  section.className = "daily-dashboard";
  section.setAttribute("aria-labelledby", "today-title");
  section.innerHTML = `
    <div class="daily-heading">
      <div>
        <p class="eyebrow">世界の工場で進む自動化</p>
        <h1 id="today-title">工場の自動化は、<br>どこまで進んでいる？</h1>
        <p class="lead">ロボット、無人搬送、画像検査などの導入を、計画・発注・導入・実運用に分けて、企業や政府の公表から追います。</p>
      </div>
      <p id="daily-asof" class="daily-asof">情報を読み込んでいます。</p>
    </div>

    <div id="daily-latest" class="daily-latest" aria-live="polite">
      <p class="daily-loading">最新の動きを読み込んでいます。</p>
    </div>

    <div id="daily-counts" class="daily-counts" aria-label="工場の自動化状況"></div>

    <div class="daily-history">
      <div class="section-title">
        <div>
          <p class="kicker">最近の動き</p>
          <h2>最近確認された変化</h2>
        </div>
        <a class="daily-explore-link" href="#explorer">全工場を探す ↓</a>
      </div>
      <div id="daily-events" class="daily-events"></div>
    </div>

    <p id="daily-status" class="status-line" aria-live="polite"></p>
  `;
  main.insertBefore(section, explorer);

  const nav = document.querySelector(".topbar nav");
  if (nav && !nav.querySelector('a[href="#today"]')) {
    const link = document.createElement("a");
    link.href = "#today";
    link.textContent = "最新動向";
    nav.insertBefore(link, nav.firstChild);
  }
}

function sortRecords(records) {
  return [...records].sort((a, b) => {
    const date = String(b.observed_at || "").localeCompare(String(a.observed_at || ""));
    if (date !== 0) return date;
    return String(b.source_published_at || "").localeCompare(String(a.source_published_at || ""));
  });
}

function renderLatest(record) {
  const source = record.source_url
    ? `<a href="${escapeHtml(record.source_url)}" target="_blank" rel="noreferrer">一次情報を見る →</a>`
    : '<span class="missing">一次情報URL未収録</span>';
  document.querySelector("#daily-latest").innerHTML = `
    <article class="daily-feature">
      <div class="daily-feature-topline">
        <span class="daily-label">最新確認 · ${escapeHtml(statusLabel[record.status] || record.status)}</span>
        <time datetime="${escapeHtml(record.observed_at)}">${escapeHtml(formatDate(record.observed_at))}</time>
      </div>
      <h2>${escapeHtml(record.company)}</h2>
      <p class="daily-place">${escapeHtml(record.factory)} · ${escapeHtml(record.country)}</p>
      <p class="daily-description">${escapeHtml(record.description)}</p>
      <div class="daily-evidence-row">
        <span>${escapeHtml(humanize(record.equipment_type))}</span>
        ${source}
      </div>
    </article>
  `;
}

function renderCounts(index) {
  const counts = index.coverage?.status_counts || {};
  document.querySelector("#daily-counts").innerHTML = statusOrder.map(status => `
    <div class="daily-count-card" data-status="${status}">
      <strong>${Number(counts[status] || 0).toLocaleString("ja-JP")}</strong>
      <span>${escapeHtml(statusLabel[status])}</span>
    </div>
  `).join("");
}

function renderEvents(records) {
  document.querySelector("#daily-events").innerHTML = records.slice(0, 6).map(record => `
    <article class="daily-event">
      <div>
        <time datetime="${escapeHtml(record.observed_at)}">${escapeHtml(formatDate(record.observed_at))}</time>
        <span class="daily-event-status">${escapeHtml(statusLabel[record.status] || record.status)}</span>
      </div>
      <h3>${escapeHtml(record.company)} · ${escapeHtml(record.factory)}</h3>
      <p>${escapeHtml(humanize(record.equipment_type))}</p>
      ${record.source_url ? `<a href="${escapeHtml(record.source_url)}" target="_blank" rel="noreferrer" aria-label="${escapeHtml(record.company)} ${escapeHtml(record.factory)} の一次情報を見る">一次情報 ↗</a>` : ""}
    </article>
  `).join("");
}

async function loadDailyDashboard() {
  injectDashboard();
  try {
    const [indexResponse, recordsResponse] = await Promise.all([
      fetch("api/v1/robotics/index.json"),
      fetch("api/v1/robotics/records.json"),
    ]);
    if (!indexResponse.ok) throw new Error(`robotics index HTTP ${indexResponse.status}`);
    if (!recordsResponse.ok) throw new Error(`robotics records HTTP ${recordsResponse.status}`);

    const [index, payload] = await Promise.all([indexResponse.json(), recordsResponse.json()]);
    const records = sortRecords(payload.records || []);
    if (!records.length) throw new Error("verified robotics records are empty");

    renderLatest(records[0]);
    renderCounts(index);
    renderEvents(records);
    document.querySelector("#daily-asof").textContent = `一次情報の最終取得: ${formatTimestamp(index.retrieved_at)}`;
    document.querySelector("#daily-status").textContent = `${index.coverage.observation_count.toLocaleString("ja-JP")}件の公開情報を収録。表示日付は各事実が確認された日です。`;
  } catch (error) {
    console.error("Failed to load robotics dashboard", error);
    document.querySelector("#daily-latest").innerHTML = '<div class="empty-state">工場自動化の最新情報を表示できません。</div>';
    document.querySelector("#daily-counts").innerHTML = "";
    document.querySelector("#daily-events").innerHTML = "";
    document.querySelector("#daily-asof").textContent = "最新情報の取得状況を確認できません。";
    document.querySelector("#daily-status").className = "status-line error";
    document.querySelector("#daily-status").textContent = "データを読み込めませんでした。ページを再読み込みしてください。";
  }
}

loadDailyDashboard();
