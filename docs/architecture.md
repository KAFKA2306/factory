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

## 配信

- FastAPI: `/v1/*`
- GitHub Pages: `web/`
- JSONL: 研究・分析用途
- `catalog.json`: ブラウザ向け一括配信

## 更新

1. 公式ソースアダプターが候補を取得
2. 出典URL、取得日、根拠箇所を付与
3. Pydantic検証
4. 参照整合性と国別カバレッジを監査
5. 静的カタログを生成
6. 差分をPull Requestとしてレビュー
