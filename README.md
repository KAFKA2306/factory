# FactoryDB

公式一次情報に基づいて、世界の企業・工場をデータベース化し、API・JSONL・Web UIで配信するプロジェクトです。

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

ISO 3166-1の249コードは国・地域プロファイルとして保持しますが、工場収録国数を249まで増やすことは現在の完成条件ではありません。**工場レコード収録国・地域は179件を現行スコープの上限**とし、以後は件数拡大より、既存レコードの一次情報、粒度、工程・製品・設備・投資・財務の品質と保守性を優先します。

公式一次情報から「該当する工場が存在しない」と確認できる場合は `verified_no_qualifying_factory` として根拠付きで保持します。未収録国・地域を件数達成のために架空・弱い根拠・重複レコードで埋めることはしません。

179件を超える国・地域へのcoverage拡張は通常の保守対象ではなく、明示的なスコープ変更として別途判断します。

## 対象領域

- 資産: 生産ライン、製造装置、工場建屋、ユーティリティ
- 製品: 完成品、部材、中間体
- 製造工程: 組立、加工、成膜、鋳造、鍛造、プレス、電池製造等
- 規模: 生産能力、面積、従業員、稼働開始
- バランスシート: 総資産、負債、資本、設備投資
- 投資: 金額、通貨、発表日、対象工場、目的、進捗
- オントロジー: ISICと独自工程・設備語彙
- 配信: FastAPI、GitHub Pages、JSONL

## 実行

```bash
python -m pip install -e '.[dev]'
python -m factorydb.validate
python -m factorydb.coverage_validation
python scripts/build_catalog.py
uvicorn factorydb.api:app --reload
```

静的UIは `web/index.html` を配信してください。

## API

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

通常CIはスキーマ、参照整合性、全249国・地域プロファイル、架空データ禁止、非該当判定と工場レコードの重複、179国coverage上限を検証します。

```bash
python -m factorydb.coverage_validation
```

この検証は現在のcoverage状態を監査しますが、未収録国・地域を自動的な未完了バックログにはしません。品質改善では、既存179国の一次情報の強度、重複排除、粒度、製品・工程・設備・投資・財務データの充実を優先します。

`factory_missing_countries` と `coverage_missing_countries` は現況を観測するための互換メトリクスとして残します。これらが0になることはリリース条件ではありません。

FY2026財務レコードには、営業収益・利益だけでなく、総資産、負債、株主資本、営業・投資・財務キャッシュフローの公式絶対額を百万円単位で格納しています。

詳細: [アーキテクチャ](docs/architecture.md) / [データポリシー](docs/data-policy.md)
