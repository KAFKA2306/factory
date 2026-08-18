# アーキテクチャ

## 正準データ

`data/*.jsonl` が正準です。UI用の `web/catalog.json` は生成物であり、直接編集しません。

## ドメイン

- `Country`: ISO 3166-1の国・地域マスターと国別産業指標
- `Company`: 法人・企業グループ
- `Facility`: 物理工場、製造会社、複数サイトを束ねた製造拠点群
- `Asset`: 生産ライン、炉、成膜装置、組立設備等
- `Investment`: 金額、通貨、発表日、対象拠点、目的
- `FinancialSnapshot`: IFRS、US GAAP、J-GAAP等の財務スナップショット
- `OntologyTerm`: ISIC等の外部分類とfactorydb独自工程語彙

`Facility.granularity` により、物理的な単一工場と、公式資料が会社単位でしか開示しない製造会社を区別します。

## カバレッジ境界

ISO 3166-1の249コードは国・地域マスターとして保持します。一方、工場レコードの収録国・地域は179件を現行スコープ上限とし、全249コードへ工場coverageを広げることをアーキテクチャ上の完成条件にはしません。

`coverage_missing_countries` 等は現況観測と後方互換のために算出しますが、値を0へ近づけること自体を自動作業の目的にしません。通常の拡充対象は既存coverage内の出典、粒度、製品、工程、設備、投資、財務です。

## Provenance

正準レコードのcitationは、公式一次情報のpublisher、URL、取得日、根拠箇所を保持します。`GET /v1/source-evidence/{entity_id}` とMCP `get_source_evidence` は同じqueryからcitationと `factorydb.provenance.v1` envelopeを返します。

core citationが保持していない情報を埋めません。

- `source_observed_at`: citationの`retrieved_at`
- `source_id`: source URLから作る安定ID。source本文hashではない
- `source_hash`: raw source本文をcoreが保存していないため`null`
- `freshness`: source別の更新周期を定義していないため`unknown`
- `stale`: freshness policyがないため`null`
- `data_as_of`: citationだけからsource内の対象期間を決められないため`null`
- `generated_at`: on-demand responseに永続generation timestampを作らないため`null`
- `null_reason`: 上記null/unknownの理由
- `basis`: citationのevidence text

Robotics evidenceは別途raw source snapshotのSHA-256を保持します。そのhashをcore citationの`source_hash`へ転用しません。複数sourceの意味が矛盾する場合も、一方を推測で正本へ上書きせず、解消できるまで正常値として追加しません。

`GET /v1/data-health` / MCP `get_data_health` はcitation数、最新取得日、core source-content hashが未保持であること、freshness policy未定義であることを明示します。

## 配信

- FastAPI: `/v1/*`
- MCP Streamable HTTP: `/mcp`
- GitHub Pages: `web/`
- JSONL: 研究・分析用途
- `catalog.json`: ブラウザ向け一括配信

RESTとMCPは`factorydb.queries`を共有します。会社・工場検索、coverage、source evidence、data healthを別DBへ複製しません。

RESTでは、従来のcollection endpointに加えて `GET /v1/source-evidence/{entity_id}` と `GET /v1/data-health` を提供します。`/v1/companies` と `/v1/facilities` のfilter/limitもMCPと同じquery関数へ委譲します。

MCPのread-only tool catalogは次です。`tools/list`で同じ一覧を発見でき、CIでも代表tool callを実行します。

- `search_companies`
- `search_facilities`
- `get_facility`
- `get_facilities_batch`
- `get_country_coverage`
- `get_coverage_resolution`
- `get_products`
- `get_processes`
- `get_assets`
- `get_investments`
- `get_financials`
- `get_ontology`
- `get_source_evidence`
- `get_data_health`

MCP standaloneは`127.0.0.1`へbindし、SDKのlocalhost DNS-rebinding protectionを使います。実ホストへ出す場合は `FACTORYDB_MCP_ALLOWED_HOSTS` と、browser clientを許可する場合のみ `FACTORYDB_MCP_ALLOWED_ORIGINS` を明示します。HostなしでOriginだけ設定した場合は起動時に失敗します。MCP request bodyは1 MiBを上限とし、tool側も一覧・batchを最大100件に制限します。

## 更新

1. 公式ソースアダプターが候補を取得
2. 出典URL、取得日、根拠箇所を付与
3. Pydantic検証
4. 参照整合性とcoverage scopeを監査
5. 静的カタログを生成
6. 差分をPull Requestとしてレビュー
