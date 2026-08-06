# FactoryDB

公式一次情報に基づいて、世界の企業・工場をデータベース化し、API・JSONL・Web UIで配信するプロジェクトです。

## 現在の実データ

- ISO 3166-1 国・地域プロファイル: **249件**
- 実在する工場・製造拠点: **30件**
- 工場レコード収録国・地域: **28件**
- 企業: **1社**
- 設備資産: **2件**
- 投資案件: **2件**
- 財務スナップショット: **1件**

初期工場データは、Toyota Motor Corporationが2026年5月8日時点で公開した世界生産拠点情報を正規化したものです。架空データ、サンプル、ダミー値は含みません。

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
python scripts/build_catalog.py
uvicorn factorydb.api:app --reload
```

静的UIは `web/index.html` を配信してください。

## API

- `GET /health`
- `GET /v1/coverage`
- `GET /v1/countries`
- `GET /v1/companies`
- `GET /v1/facilities?country=JP&process=vehicle_assembly`
- `GET /v1/assets`
- `GET /v1/investments`
- `GET /v1/financials`
- `GET /v1/ontology`

## データ更新

```bash
python scripts/sync_worldbank.py
python scripts/sync_sec_companyfacts.py
python -m factorydb.validate
python scripts/build_catalog.py
```

World Bank APIは各国の製造業付加価値等を更新し、SEC Companyfacts APIは法定開示の財務値を更新します。

## 品質ゲート

通常CIはスキーマ、参照整合性、全249国・地域プロファイル、架空データ禁止を検証します。

全ての国・地域に工場が最低1件あることを要求する厳格監査:

```bash
python -m factorydb.validate --require-factory-every-country
```

この厳格ゲートが未達の間は、UIに未収録国数を表示し、完成済みとは扱いません。

詳細: [アーキテクチャ](docs/architecture.md) / [データポリシー](docs/data-policy.md)
