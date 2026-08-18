# FactoryDB

[![CI](https://github.com/KAFKA2306/factory/actions/workflows/ci.yml/badge.svg)](https://github.com/KAFKA2306/factory/actions/workflows/ci.yml)
[![Deploy Pages](https://github.com/KAFKA2306/factory/actions/workflows/pages.yml/badge.svg)](https://github.com/KAFKA2306/factory/actions/workflows/pages.yml)
[![Refresh official data](https://github.com/KAFKA2306/factory/actions/workflows/refresh.yml/badge.svg)](https://github.com/KAFKA2306/factory/actions/workflows/refresh.yml)
[![Robotics evidence](https://github.com/KAFKA2306/factory/actions/workflows/robotics-evidence.yml/badge.svg)](https://github.com/KAFKA2306/factory/actions/workflows/robotics-evidence.yml)

**「どの会社が、どこで、何を、どう作っているか」を、出典まで戻って比較できる製造拠点データベース。**

企業サイト、政府資料、規制開示には工場情報があります。しかし、拠点名だけ集めても、製品・工程・設備・投資・生産能力の粒度が揃わず、「0件」と「公式確認済みで該当なし」も区別できません。

FactoryDB は、企業・工場・製品・工程・設備・投資・財務を公式一次情報へ接続し、**世界の製造拠点を比較できる形へ正規化して配信する**プロジェクトです。

## Vision

工場DBを「地図上の点」から、**企業の製造戦略を拠点単位で理解できる調査基盤**へ変えます。

利用者が知りたいのは、工場が存在するかだけではありません。

- その拠点で何を作っているか
- どの工程を担っているか
- 生産能力・設備・従業員・面積はどの程度か
- どの投資案件と結びついているか
- その情報は企業公式・政府・規制開示のどれに基づくか
- 情報がないのか、本当に該当拠点がないのか

FactoryDB は、この判断を一つの検索・API・MCPから行える状態を目指します。

## Design philosophy

- **coverageより意味を優先する。** 国数を増やすためのダミー工場や推測値を入れない。
- **0件と確認済み非該当を分ける。** `verified_no_qualifying_factory` を独立stateとして保持する。
- **一次情報へ戻れることを必須にする。** 企業IR、政府機関、規制当局等のsourceをrecordと結びつける。
- **企業・工場・製品・工程を混ぜない。** entity間の関係として保持し、1行の説明へ潰さない。
- **REST / MCP / Webで別の真実を作らない。** `factorydb.queries` の同じread modelを共有する。
- **取得できない情報を“それらしく”補完しない。** 未取得・未確認・非開示を状態として残す。

## Why / 差別化

一般的な工場一覧は「会社名・工場名・所在地」で終わりがちです。FactoryDB は、**拠点を企業戦略・製品・工程・設備・投資・財務へ接続し、さらに各主張の一次情報まで逆引きできること**を差別化の中心に置きます。

ISO 3166-1、ISIC、FastAPI、MCP、JSONL は価値そのものではありません。これらは、国や企業をまたいでも比較条件を揃え、出典・未確認state・関係性を失わないための手段です。

## 現在のcoverage

現在のmainでは次を正準データとして扱います。

- ISO 3166-1 国・地域プロファイル: 249
- 実在する工場・製造拠点: 202
- 工場レコード収録国・地域: 179
- 公式根拠付き非該当地域: 5
- 企業: 129

179国・地域は現行スコープ上限です。以後の通常改善は国数の拡張より、**既存recordのsource強度、製品・工程・設備・投資・財務の粒度**を優先します。

現在値はvalidationと生成catalogを優先し、READMEの数字を正本とはしません。

## Robotics evidence

ARK Big Ideas 2026 の Robotics を、工場単位の一次情報で検証する正準layerです。

- 入力ledger: [`data/automation.jsonl`](data/automation.jsonl)
- 一次source registry: [`data/robotics-sources.json`](data/robotics-sources.json)
- API index: [`api/v1/robotics/index.json`](api/v1/robotics/index.json)
- 全record: [`api/v1/robotics/records.json`](api/v1/robotics/records.json)
- FactoryDB coreとのidentity照合: [`api/v1/robotics/identity-coverage.json`](api/v1/robotics/identity-coverage.json)

`planned / ordered / installed / operational` は別statusです。robot数・automation率などは一次sourceが明示した場合だけ保持し、企業全体や複数工場の合計を個別工場へ配分しません。一次ページはworkflowでlive検証してSHA-256 evidenceとして保存し、APIをraw evidenceだけからoffline再生成して差分検証します。

## 利用者ができること

- 国・企業・工程で工場を検索する
- 工場と製品・工程・設備を辿る
- 投資案件から対象工場へ戻る
- coverage未解決国と公式非該当地域を区別する
- source evidenceを確認する
- REST / MCPの同じread modelから再利用する

## Domain model

```text
Company
  └─ Facility
       ├─ Product
       ├─ Process
       ├─ Asset
       ├─ Capacity / Scale
       └─ Investment

Company
  └─ Financial Snapshot

Every claim
  └─ Source evidence
```

対象領域:

- 資産: 生産ライン、製造装置、建屋、ユーティリティ
- 製品: 完成品、部材、中間体
- 工程: 組立、加工、成膜、鋳造、鍛造、プレス、電池製造等
- 規模: 生産能力、面積、従業員、稼働開始
- 投資: 金額、通貨、発表日、対象工場、目的、進捗
- 財務: 資産、負債、資本、CF、設備投資

## REST API

主なendpoint:

```text
GET /health
GET /v1/coverage
GET /v1/coverage-resolutions
GET /v1/countries
GET /v1/companies
GET /v1/facilities?country=JP&process=vehicle_assembly
GET /v1/products
GET /v1/processes
GET /v1/assets
GET /v1/investments
GET /v1/financials
GET /v1/ontology
```

## MCP

RESTとMCPは別々のDBや計算を持ちません。

```text
http://127.0.0.1:8000/mcp
```

MCP単体:

```bash
factorydb-mcp
```

source不明・coverage未解決をMCP側で推測補完しません。

## EDINETDB consumer boundary

FactoryDBはEDINETDBへ直接アクセスせず、共有quota-ownerが取得したprojectionを第二経路として読みます。

`data/financials.jsonl` の企業IR等に基づく値が正本で、EDINETDB projectionは自動上書きしません。

詳細: [docs/edinetdb-consumer.md](docs/edinetdb-consumer.md)

## 実行

fresh cloneでは `uv` でlockfileどおりの環境を作り、同じ入口をlocal/CIで使います。Node.js 22は静的Webの小さなJavaScript検査にだけ使います。

```bash
make bootstrap
make check
uv run factorydb-api
```

静的UIは `web/index.html` を配信します。

## データ更新

```bash
uv run python scripts/sync_worldbank.py
uv run python scripts/sync_sec_companyfacts.py
make check
```

World Bank / SEC由来値もsource・単位・期間を持つ入力として扱い、既存一次情報を無条件で上書きしません。

## Quality gate

`make check` がlocalとCIの共通入口です。役割を重複させません。

- **uv**: Python環境と`uv.lock`整合性
- **Ruff**: Python format / lint
- **Pyrefly**: `src/factorydb` のstatic type check
- **Pydantic**: 外部JSONL/API入力を読むruntime boundaryのvalidation
- **Node.js標準機能**: dependencyを持たないPages JavaScriptのsyntax / URL-state test

Biome / Oxlint / tsc / Zodは、現在TypeScript/npm dependency graphがないため導入しません。Nxはmulti-project monorepoではないため不要です。prekも別のhook実行系を増やさず、`make check`を単一のlocal gateとして使います。

CIではさらにcoverage evidenceとFacility Verification Packをartifactとして残します。`make check`はschema/reference integrity、249 profile、架空data禁止、coverage state、REST/MCP parity、Robotics evidence、生成catalogまで検証します。

`factory_missing_countries == 0` は完成条件ではありません。

## Repository map

```text
factorydb/        domain model / queries / API / MCP
data/             canonical JSONL data
scripts/          sync / build / validation
web/              static UI
docs/             architecture / policy / consumer contracts
tests/            deterministic contracts
```

- [Architecture](docs/architecture.md)
- [Data policy](docs/data-policy.md)
- [EDINETDB consumer contract](docs/edinetdb-consumer.md)

## Done

FactoryDB の成功指標は「世界何か国に点を置いたか」ではありません。

**利用者が、ある企業の製造拠点について「何を作る・どう作る・どの投資と結びつく・何を根拠にそう言える」を同じ証拠線上で確認できること**をDoneとします。
