# EDINETDB consumer contract

FactoryDBはEDINETDBへ直接アクセスしません。

EDINETDB Freeの認証付きリクエストは100 requests/dayで、REST APIとMCPを含めて同一アカウント単位で合算されます。複数repositoryが同じ企業を個別取得するとquotaを重複消費するため、`KAFKA2306/semiconductor-earnings-model`のquota-ownerが取得を集約します。

一次情報:

- https://edinetdb.jp/docs/mcp-guide
- https://edinetdb.jp/docs/api
- https://edinetdb.jp/legal/terms

## データ経路

```text
EDINETDB
  -> quota ownerで重複排除・batch fetch
  -> raw responseは保存しない
  -> KAFKA2306/factory専用field projection
  -> GitHub上の共有projection
  -> FactoryDB audit
  -> canonical dataは変更しない
```

FactoryDB用projection:

```text
https://raw.githubusercontent.com/KAFKA2306/semiconductor-earnings-model/main/
data/edinetdb_projections/KAFKA2306__factory/factory-toyota-financials.json
```

projectionがまだ生成されていない場合、FactoryDB側からEDINETDBへfallbackアクセスしてはいけません。中央quota-ownerの次回同期を待つか、quota-ownerを明示手動実行します。

## なぜraw cacheを共有しないか

EDINETDB利用規約は、自身のapplication/dashboard/reportへの組み込みと一時cacheを認めていますが、API/MCP responseの全部または大部分をファイルやDBとして第三者へ一括再配布すること、実質同等のwrapper/proxy APIを作ることを禁止しています。

そのため共有projectionはFactoryDBが実際に監査で使うfieldだけです。`Powered by EDINET DB` attribution、request fingerprint、response SHA-256を保持し、full responseは保持しません。

## FactoryDBでの役割

FactoryDBの財務正本は引き続き企業公式IR・法定開示等の一次資料に基づく`data/financials.jsonl`です。

EDINETDB projectionは正本を上書きせず、XBRL正規化された第二経路として数値のcross-checkに使います。

`/financials`の金額はEDINETDB公式仕様上すべて円単位です。FactoryDBはrecordごとの`scale`（現在のToyota FY2026は`million`）へ変換して比較します。

## 実行

中央projectionを直接監査:

```bash
python scripts/audit_edinetdb_projection.py --require-match
```

fixtureや保存済みprojectionを使う場合:

```bash
python scripts/audit_edinetdb_projection.py \
  --projection-file path/to/projection.json \
  --require-match
```

出力:

```text
audit/edinetdb-projection-audit.json
```

## fail-close

次は失敗扱いです。

- consumerが`KAFKA2306/factory`ではない
- `Powered by EDINET DB` attributionがない
- request fingerprint / raw response SHA-256がない
- schemaが未対応
- 比較可能な数値が1件もない
- 比較可能な数値が許容差を超えて不一致

この監査はEDINETDBを呼ばないため、何回実行してもEDINETDB quotaを消費しません。
