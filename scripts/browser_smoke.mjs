import {execFileSync, spawn} from "node:child_process";

const targetUrl = process.argv[2];
const expectedCommit = process.argv[3] || "";
if (!targetUrl) throw new Error("usage: node scripts/browser_smoke.mjs <url> [expected-commit]");

const chrome = execFileSync(
  "bash",
  ["-lc", "command -v google-chrome || command -v google-chrome-stable || command -v chromium || command -v chromium-browser"],
  {encoding: "utf8"},
).trim();
if (!chrome) throw new Error("Chrome/Chromium is required for the browser smoke test");

const port = 9200 + Math.floor(Math.random() * 500);
const profile = `/tmp/factorydb-chrome-${process.pid}`;
const browser = spawn(chrome, [
  "--headless=new",
  "--disable-gpu",
  "--no-sandbox",
  `--remote-debugging-port=${port}`,
  `--user-data-dir=${profile}`,
  "about:blank",
], {stdio: ["ignore", "ignore", "inherit"]});

const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

async function retry(fn, attempts = 400) {
  let lastError;
  for (let index = 0; index < attempts; index += 1) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;
      await sleep(100);
    }
  }
  throw lastError;
}

let socket;
let nextId = 1;
const pending = new Map();
const eventWaiters = new Map();

function waitForEvent(method) {
  return new Promise(resolve => {
    const queue = eventWaiters.get(method) || [];
    queue.push(resolve);
    eventWaiters.set(method, queue);
  });
}

async function rpc(method, params = {}) {
  const id = nextId;
  nextId += 1;
  const response = new Promise((resolve, reject) => pending.set(id, {resolve, reject}));
  socket.send(JSON.stringify({id, method, params}));
  return response;
}

async function evaluate(expression) {
  const response = await rpc("Runtime.evaluate", {
    expression,
    awaitPromise: true,
    returnByValue: true,
  });
  if (response.exceptionDetails) {
    throw new Error(response.exceptionDetails.exception?.description || "browser evaluation failed");
  }
  return response.result.value;
}

async function navigate(url) {
  const loaded = waitForEvent("Page.loadEventFired");
  await rpc("Page.navigate", {url});
  await loaded;
  await evaluate(`(async () => {
    for (let i = 0; i < 100; i += 1) {
      const status = document.querySelector("#page-status")?.textContent || "";
      if (status.includes("データを読み込みました")) return status;
      if (status.includes("失敗しました")) throw new Error(status);
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    throw new Error("FactoryDB did not finish loading");
  })()`);
}

async function verifyErrorState(url) {
  await rpc("Network.setCacheDisabled", {cacheDisabled: true});
  await rpc("Fetch.enable", {
    patterns: [{urlPattern: "*catalog.json*", requestStage: "Request"}],
  });
  const paused = waitForEvent("Fetch.requestPaused");
  const loaded = waitForEvent("Page.loadEventFired");
  await rpc("Page.navigate", {url});
  const request = await paused;
  await rpc("Fetch.failRequest", {requestId: request.requestId, errorReason: "Failed"});
  await loaded;
  const errorState = await evaluate(`(async () => {
    for (let i = 0; i < 100; i += 1) {
      const status = document.querySelector("#page-status")?.textContent || "";
      if (status.includes("データ読み込みに失敗しました")) {
        return {
          status,
          emptyVisible: !document.querySelector("#empty-state").hidden,
          facilityCount: document.querySelectorAll(".factory-card").length,
        };
      }
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    throw new Error("error state did not become visible");
  })()`);
  await rpc("Fetch.disable");
  await rpc("Network.setCacheDisabled", {cacheDisabled: false});
  if (!errorState.emptyVisible || errorState.facilityCount !== 0) {
    throw new Error(`error state retained stale results: ${JSON.stringify(errorState)}`);
  }
  return errorState;
}

try {
  const version = await retry(async () => {
    const response = await fetch(`http://127.0.0.1:${port}/json/version`);
    if (!response.ok) throw new Error(`DevTools HTTP ${response.status}`);
    return response.json();
  });
  if (!version.Browser) throw new Error("Chrome DevTools did not report a browser version");

  const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
  const page = targets.find(target => target.type === "page");
  if (!page?.webSocketDebuggerUrl) throw new Error("No Chrome page target found");

  socket = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => {
    socket.addEventListener("open", resolve, {once: true});
    socket.addEventListener("error", reject, {once: true});
  });
  socket.addEventListener("message", event => {
    const message = JSON.parse(event.data);
    if (message.id) {
      const request = pending.get(message.id);
      if (!request) return;
      pending.delete(message.id);
      if (message.error) request.reject(new Error(message.error.message));
      else request.resolve(message.result || {});
      return;
    }
    const queue = eventWaiters.get(message.method);
    if (queue?.length) queue.shift()(message.params || {});
  });

  await rpc("Page.enable");
  await rpc("Runtime.enable");
  await rpc("Network.enable");
  await rpc("Input.setIgnoreInputEvents", {ignore: false});

  if (expectedCommit) {
    const deploymentUrl = new URL("deployment.json", targetUrl);
    const deployment = await retry(async () => {
      const response = await fetch(deploymentUrl, {cache: "no-store"});
      if (!response.ok) throw new Error(`deployment.json HTTP ${response.status}`);
      return response.json();
    }, 120);
    if (deployment.source_commit !== expectedCommit) {
      throw new Error(`production commit ${deployment.source_commit} != expected ${expectedCommit}`);
    }
  }

  await navigate(targetUrl);

  const freshness = await evaluate(`(() => document.querySelector("#freshness-state")?.textContent || "")()`);
  if (!freshness.includes("freshness policyは未定義") || !freshness.includes("stale / fresh は断定しません")) {
    throw new Error(`freshness uncertainty is not explicit: ${freshness}`);
  }

  const journey = await evaluate(`(() => {
    const query = document.querySelector("#query");
    query.value = "Toyota";
    query.dispatchEvent(new Event("input", {bubbles: true}));
    const cards = [...document.querySelectorAll(".factory-card")];
    if (cards.length < 2) throw new Error("search returned fewer than two facilities");
    cards[0].querySelector(".compare-button").click();
    cards[1].querySelector(".compare-button").click();
    const comparison = document.querySelector("#comparison-table");
    return {
      status: document.querySelector("#comparison-status").textContent,
      table: comparison.textContent,
      sourceLinks: comparison.querySelectorAll('a[href^="http"]').length,
      href: location.href,
      count: cards.length,
    };
  })()`);
  if (!journey.status.includes("2拠点を比較中")) throw new Error(journey.status);
  if (journey.sourceLinks < 2) throw new Error("comparison does not expose enough primary-source links");
  if (!journey.href.includes("compare=")) throw new Error("comparison state was not written to the URL");
  if (!journey.href.includes("q=Toyota")) throw new Error("search state was not written to the URL");

  await navigate(journey.href);
  const restored = await evaluate(`(() => ({
    status: document.querySelector("#comparison-status").textContent,
    table: document.querySelector("#comparison-table").textContent,
    query: document.querySelector("#query").value,
  }))()`);
  if (!restored.status.includes("2拠点を比較中") || restored.query !== "Toyota") {
    throw new Error("shared URL did not restore the comparison/search state");
  }

  const emptyState = await evaluate(`(() => {
    const query = document.querySelector("#query");
    query.value = "__factorydb_no_result__";
    query.dispatchEvent(new Event("input", {bubbles: true}));
    const empty = document.querySelector("#empty-state");
    return {
      visible: !empty.hidden,
      text: empty.textContent,
      cards: document.querySelectorAll(".factory-card").length,
    };
  })()`);
  if (!emptyState.visible || emptyState.cards !== 0 || !emptyState.text.includes("現在の検索結果が0件")) {
    throw new Error(`empty result semantics are unclear: ${JSON.stringify(emptyState)}`);
  }

  await navigate(journey.href);
  await rpc("Input.dispatchKeyEvent", {type: "keyDown", key: "Tab", code: "Tab", windowsVirtualKeyCode: 9});
  await rpc("Input.dispatchKeyEvent", {type: "keyUp", key: "Tab", code: "Tab", windowsVirtualKeyCode: 9});
  const keyboard = await evaluate(`(() => {
    const active = document.activeElement;
    const style = getComputedStyle(active);
    return {tag: active?.tagName || "", outline: style.outlineStyle, width: active?.getBoundingClientRect().width || 0};
  })()`);
  if (!keyboard.tag || keyboard.tag === "BODY" || keyboard.width <= 0 || keyboard.outline === "none") {
    throw new Error(`keyboard focus is not visibly exposed: ${JSON.stringify(keyboard)}`);
  }

  await rpc("Emulation.setDeviceMetricsOverride", {
    width: 320,
    height: 900,
    deviceScaleFactor: 1,
    mobile: false,
  });
  await rpc("Emulation.setPageScaleFactor", {pageScaleFactor: 2});
  const reflow = await evaluate(`(() => ({
    rootScrollWidth: document.documentElement.scrollWidth,
    rootClientWidth: document.documentElement.clientWidth,
    comparisonOverflow: document.querySelector("#comparison-table").scrollWidth >= document.querySelector("#comparison-table").clientWidth,
  }))()`);
  if (reflow.rootScrollWidth > reflow.rootClientWidth + 1) {
    throw new Error(`page overflows at 320px/200%: ${JSON.stringify(reflow)}`);
  }

  await rpc("Emulation.clearDeviceMetricsOverride");
  await rpc("Emulation.setPageScaleFactor", {pageScaleFactor: 1});
  const errorState = await verifyErrorState(new URL("?browser_error_state=1", targetUrl).href);

  console.log(JSON.stringify({
    browser: version.Browser,
    target: targetUrl,
    expectedCommit: expectedCommit || null,
    searchResults: journey.count,
    comparisonSourceLinks: journey.sourceLinks,
    shareRestore: true,
    emptyState,
    errorState,
    freshnessState: freshness,
    keyboardFocus: keyboard,
    narrowZoom: reflow,
  }, null, 2));
} finally {
  if (socket?.readyState === WebSocket.OPEN) socket.close();
  browser.kill("SIGTERM");
}
