# FactoryDB

**「どの会社が、どこに工場を持つか」だけでは、世界の製造拠点は比較できない。**

同じ企業でも拠点ごとに製品・工程・設備・投資規模が違い、公開情報の粒度も揃いません。さらに「工場レコードが0件」と「公式一次情報で該当工場なしを確認済み」は別の状態です。そこを混ぜると、coverageの数字だけが増えて中身が分からなくなります。

FactoryDBは、企業・工場・製品・工程・設備・投資・財務を公式一次情報と結びつけ、ISO 3166-1、ISIC、JSONLを使って整理し、REST API・MCP・Web UIで配信するプロジェクトです。0件と「該当なし確認済み」を分離し、一次情報で確認できた範囲だけをデータとして保持します。

ISO 3166-1の249国・地域プロファイルを保持しつつ、工場レコード収録国・地域は **179件を現行スコープ上限** とし、以後は件数拡大より既存レコードの出典強度、粒度、製品・工程・設備・投資・財務の品質を優先します。

## 現在の実データ

- ISO 3166-1 国・地域プロファイル: **249件**
- 実在する工場・製造拠点: **202件**
- 工場レコード収録国・地域: **179件**
- 公式根拠付き非該当地域: **5件**
- 工場または非該当判定のある国・地域: **184件**
- 工場レコード0件の国・地域: **70件**
- 企業: **129社**
- 設備資産: **2件**
- 投資案件: **3件**
- 財務スナップショット: **1件**

各レコードは企業公式・政府機関・規制当局等の一次情報を出典として保持し、架空データ、サンプル、ダミー値は含みません。

企業データは後方互換を維持したまま `data/companies*.jsonl` のシャード読込に対応しています。既存の `data/companies.jsonl` は引き続き有効で、新規企業を追加シャードへ分割できます。

ISO 3166-1の249コードは国・地域マスターとして保持しますが、全249コードへ工場coverageを拡張することは現在の完成条件ではありません。公式一次情報から「該当する工場が存在しない」と確認できる場合は `verified_no_qualifying_factory` として根拠付きで保持します。179件を超えるcoverage拡張は通常保守ではなく、明示的なスコープ変更として扱います。

## 対象領域

- 資産: 生産ライン、製造装置、工場建屋、ユーティリティ
- 製品: 完成品、部材、中間体
- 製造工程: 組立、加工、成膜、鋳造、鍛造、プレス、電池製造等
- 規模: 生産能力、面積、従業員、稼働開始
- バランスシート: 総資産、負債、資本、設備投資
- 投資: 金額、通貨、発表日、対象工場、目的、進捗
- オントロジー: ISICと独自工程・設備語彙
- 配信: FastAPI、MCP、GitHub Pages、JSONL

## 実行

```bash
python -m pip install -e '.[dev]'
python -m factorydb.validate
python -m factorydb.coverage_validation
python scripts/build_catalog.py
uvicorn factorydb.api:app --reload
```

静的UIは `web/index.html` を配信してください。

## REST API

- `GET /health`
- `GET /v1/coverage`
- `GET /v1/coverage-resolutions`
- `GET /v1/countries`
- `GET /v1/companies`
- `GET /v1/facilities?country=JP&process=vehicle_assembly`
- `GET /v1/products`
- `GET /v1/processes`
- `GET /v1/assets`
- `GET /v1/investments`
- `GET /v1/financials`
- `GET /v1/ontology`

## MCP

RESTとMCPは別々の計算やDBを持たず、`factorydb.queries` の同じread modelを使用します。FastAPI起動時はStreamable HTTPのMCPを同居させます。

```text
http://127.0.0.1:8000/mcp
```

MCPだけをlocalhostで起動する場合:

```bash
factorydb-mcp
```

主要toolは企業・工場検索、工場batch取得、国別coverage、製品・工程・設備・投資・財務、ontology、source evidence、data healthです。source不明・coverage未解決を推測で埋めません。

## EDINETDB共有取得

FactoryDBはEDINETDBへ直接アクセスしません。認証付きquotaの重複消費を避けるため、共有quota-ownerが一度だけ取得したFactoryDB向けprojectionを監査用の第二経路として読みます。企業IR等に基づく `data/financials.jsonl` が引き続き正本で、EDINETDB値が正本を自動上書きすることはありません。

詳細: [EDINETDB consumer contract](docs/edinetdb-consumer.md)

## データ更新

```bash
python scripts/sync_worldbank.py
python scripts/sync_sec_companyfacts.py
python -m factorydb.validate
python -m factorydb.coverage_validation
python scripts/build_catalog.py
```

World Bank APIは各国の製造業付加価値等を更新し、SEC Companyfacts APIは法定開示の財務値を更新します。

## 品質ゲート

通常CIはスキーマ、参照整合性、全249国・地域プロファイル、架空データ禁止、非該当判定と工場レコードの重複、**179国coverage上限**、MCP tool contract、REST/MCP query parity、EDINETDB consumer projectionの型・単位・fail-close挙動を検証します。

```bash
python -m factorydb.coverage_validation
```

`factory_missing_countries` と `coverage_missing_countries` は現況観測と後方互換のためのメトリクスであり、0になることはリリース条件ではありません。

FY2026財務レコードには、営業収益・利益だけでなく、総資産、負債、株主資本、営業・投資・財務キャッシュフローの公式絶対額を百万円単位で格納しています。

詳細: [アーキテクチャ](docs/architecture.md) / [データポリシー](docs/data-policy.md) / [EDINETDB consumer contract](docs/edinetdb-consumer.md)
