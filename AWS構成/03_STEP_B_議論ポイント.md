# STEP B: ApiFunc の Serverless 対応 - 議論ポイント

## 📋 現状のコード確認結果

### 既存の実装（OpenSearch Service 用）

#### 1. `backend/lambda/opensearch_client.py`
- **認証**: Basic認証（`OS_USER`, `OS_PASS`）
- **エンドポイント**: `{ENDPOINT}/{INDEX}/_search`
- **検索方式**: BM25 と k-NN を別々に実行 → RRF でマージ
- **k-NN クエリ形式**: 既に正しい形式を使用
  ```python
  {"size": size, "knn": {"field": "vector", "query_vector": q_vec, "k": size, "num_candidates": max(100, size)}}
  ```

#### 2. `backend/lambda/app.py`
- **ハンドラー**: シンプルな GET リクエスト処理
- **フィルター**: 現在は `filters={}` 固定（未実装）

#### 3. `backend/template.yaml`
- **Lambda ロール**: Bedrock 権限のみ
- **OpenSearch 権限**: 未設定（Basic認証のため）

---

## 🔍 GPT の提案の評価

### ✅ 正しい部分（採用すべき）

#### 1. 認証方式の変更
**GPT の提案**: BasicAuth → AWS4Auth (SigV4)

**評価**: ✅ **完全に正しい**
- OpenSearch Serverless は IAM 認証のみ
- `requests-aws4auth` を使用する必要がある
- サービス名は `"aoss"`

**実装方針**:
```python
from requests_aws4auth import AWS4Auth
import boto3

session = boto3.Session()
credentials = session.get_credentials()
awsauth = AWS4Auth(
    credentials.access_key,
    credentials.secret_key,
    REGION,
    "aoss",
    session_token=credentials.token
)
```

#### 2. Lambda ロールの権限追加
**GPT の提案**: `aoss:APIAccessAll`, `aoss:APISearchAll` を付与

**評価**: ✅ **正しい**
- OpenSearch Serverless へのアクセスに必要
- `template.yaml` に追加する必要がある

**実装方針**:
```yaml
Policies:
  - Statement:
      - Effect: Allow
        Action:
          - "aoss:APIAccessAll"
          - "aoss:APISearchAll"
        Resource: "*"
```

#### 3. エンドポイント URL 形式の確認
**GPT の提案**: `https://<collection>.aoss.amazonaws.com/vendor-notes/_search`

**評価**: ⚠️ **確認が必要**
- OpenSearch Serverless の Document API は `/{index}/_doc/{id}` 形式
- Search API は `/{index}/_search` 形式（`/indexes/` プレフィックスは不要）
- 既存コードの `{ENDPOINT}/{INDEX}/_search` は正しい可能性が高い

**確認事項**:
- Serverless の Search API エンドポイント形式を確認
- 既存の `{ENDPOINT}/{INDEX}/_search` で動作するか検証

---

### ⚠️ 確認が必要な部分

#### 1. 検索クエリの構造
**GPT の提案例**:
```json
{
  "query": {
    "bool": {
      "must": [
        { "match": { "text": "xxxx" } },
        {
          "knn": {
            "vector": {
              "vector": [...],
              "k": 8
            }
          }
        }
      ]
    }
  },
  "size": 10
}
```

**現状の実装**:
- BM25: `{"size": size, "query": {"bool": {"must": [...]}}}`
- k-NN: `{"size": size, "knn": {"field": "vector", "query_vector": q_vec, "k": size, "num_candidates": max(100, size)}}`
- 別々に実行してから RRF でマージ

**評価**: ⚠️ **議論が必要**

**ポイント**:
1. **ハイブリッド検索の方式**
   - 現状: BM25 と k-NN を別々に実行 → RRF でマージ（**2回の API 呼び出し**）
   - GPT 提案: 1つのクエリに BM25 と k-NN を組み合わせ（**1回の API 呼び出し**）

2. **OpenSearch Serverless のサポート**
   - OpenSearch Serverless は **ハイブリッド検索（1つのクエリに組み合わせ）をサポートしているか？**
   - 公式ドキュメントで確認が必要

3. **パフォーマンス**
   - 2回の API 呼び出し vs 1回の API 呼び出し
   - RRF の実装方法（クライアント側 vs サーバー側）

**推奨アプローチ**:
- **まず現状の方式（2回の API 呼び出し + RRF）を Serverless 対応に変更**
- 動作確認後、ハイブリッド検索（1つのクエリ）が可能か検証
- 可能であれば、パフォーマンス比較して最適な方式を選択

#### 2. フィルター機能の実装
**現状**: `filters={}` 固定（未実装）

**GPT の提案**: metadata フィルタ（vendor / date range）を実装

**評価**: ✅ **必要**
- フロントエンド（`web/components/search/Filters.tsx`）で `vendor`, `from`, `to` を送信する想定
- 現在のコードでは未実装

**実装方針**:
```python
# app.py でクエリパラメータから取得
filters = {}
if event.get("queryStringParameters"):
    if "vendor" in event["queryStringParameters"]:
        filters["vendor_name"] = event["queryStringParameters"]["vendor"]
    # date range の処理も追加

# opensearch_client.py で適用
# 既に _bm25 と _knn で filters をサポートしている
```

---

## 🎯 実装の優先順位

### Phase 1: 最小限の Serverless 対応（動作確認）
1. ✅ 認証方式を SigV4 に変更
2. ✅ エンドポイント URL を確認・修正
3. ✅ Lambda ロールに OpenSearch Serverless 権限を追加
4. ✅ 既存の検索ロジック（2回の API 呼び出し + RRF）をそのまま使用
5. ✅ 動作確認

### Phase 2: 機能追加・最適化
1. ⚠️ フィルター機能の実装（vendor, date range）
2. ⚠️ ハイブリッド検索（1つのクエリ）への移行検討
3. ⚠️ エラーハンドリングの強化
4. ⚠️ ログ出力の改善

---

## 💬 GPT との議論ポイント

### 1. 検索クエリの構造について
**質問**: OpenSearch Serverless は、1つのクエリに BM25 と k-NN を組み合わせたハイブリッド検索をサポートしていますか？

**現状の理解**:
- OpenSearch Service では、ハイブリッド検索（1つのクエリ）が可能
- OpenSearch Serverless でも同様にサポートされているか確認が必要

**推奨**:
- まずは現状の方式（2回の API 呼び出し + RRF）で Serverless 対応
- 動作確認後、ハイブリッド検索への移行を検討

### 2. エンドポイント URL 形式について
**質問**: OpenSearch Serverless の Search API のエンドポイント形式は？

**現状の理解**:
- Document API: `/{index}/_doc/{id}`（`/indexes/` プレフィックス不要）
- Search API: `/{index}/_search`（`/indexes/` プレフィックス不要？）

**確認事項**:
- 既存コードの `{ENDPOINT}/{INDEX}/_search` で動作するか
- 公式ドキュメントで確認

### 3. RRF の実装について
**質問**: OpenSearch Serverless はサーバー側で RRF をサポートしていますか？

**現状の実装**:
- クライアント側（Python）で RRF を実装
- BM25 と k-NN の結果をマージ

**確認事項**:
- サーバー側で RRF が可能なら、パフォーマンス向上の可能性
- クライアント側の実装でも問題ないか

---

## 📝 実装チェックリスト

### 必須（Phase 1）
- [ ] `opensearch_client.py` を SigV4 認証に変更
- [ ] エンドポイント URL 形式を確認・修正
- [ ] `template.yaml` に OpenSearch Serverless 権限を追加
- [ ] `requirements.txt` に `requests-aws4auth` を追加（既に追加済み）
- [ ] 動作確認（ローカル or Lambda）

### 推奨（Phase 2）
- [ ] フィルター機能の実装
- [ ] ハイブリッド検索への移行検討
- [ ] エラーハンドリングの強化
- [ ] ログ出力の改善

---

## 🔗 参考資料

- [OpenSearch Serverless API リファレンス](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/serverless-api.html)
- [OpenSearch Serverless クライアント設定](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/serverless-clients.html)
- [OpenSearch Serverless データアクセスポリシー](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/serverless-data-access.html)

