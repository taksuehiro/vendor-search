# vendor-search プロジェクト AWS 構築の全体像

## 0. ゴールとスコープ

- **ゴール**
  - STEP1：既存ベンダーの基本情報を検索・回答できるチャットボット API を AWS 上に構築
  - STEP2：各ベンダーの議事録を Notion → S3 → Bedrock → OpenSearch で取り込み、検索精度を高める基盤を構築
- **対象コンポーネント**
  - フロントエンド：Amplify（Next.js ホスティング）
  - バックエンド：API Gateway + Lambda（ApiFunc / IngestFunc, SAM）
  - データストア / 検索：OpenSearch（最小構成）
  - ベクトル化 / LLM：Amazon Bedrock（titan-embed-text-v2:0, Claude 3 Haiku）
  - データ保管：S3（議事録 Markdown）

---

## 1. 準備フェーズ

1. **AWS アカウント・リージョン**
   - 使用リージョンを決定（例：`ap-northeast-1`）
2. **命名ルールの決定**
   - S3 バケット名：`vendor-search-notes-{env}`
   - OpenSearch ドメイン名：`vendor-search-{env}`
   - Lambda 関数名：`vendor-search-api-{env}`, `vendor-search-ingest-{env}` など
3. **IAM とセキュリティの基本方針**
   - Lambda 実行ロール（API 用 / Ingest 用）
   - OpenSearch へのアクセスは「IAM 認証 + IP 制限」を基本とする
4. **ローカル開発環境**
   - AWS CLI / SAM CLI / Python 3.11
   - `backend/` ディレクトリで `sam build` が通る状態を確認

---

## 2. バックエンド基盤構築（STEP1）

### 2-1. OpenSearch ドメインの作成（最小構成）

- 用途：ベクトル検索 & メタデータ検索
- 構成案（低コスト）
  - デプロイタイプ：開発 / テスト
  - インスタンス：`t3.small.search` × 1（シングル AZ）
  - ストレージ：10〜20 GB
- アクセス制御
  - 開発段階は「自分のグローバル IP + Lambda 実行ロール」を許可
- インデックス設計（例：`vendors`）
  - フィールド例
    - `id`（ドキュメントID）
    - `vendor_name`
    - `date`
    - `content`（テキスト全文）
    - `vector`（ベクトルフィールド）

### 2-2. Bedrock 設定

- 対象リージョンで Bedrock を有効化
- 使用モデル
  - 埋め込み：`amazon.titan-embed-text-v2:0`（`:0` 必須）
  - 生成：`anthropic.claude-3-haiku`
- Lambda 実行ロールに `bedrock:InvokeModel` などを付与

### 2-3. API Lambda（ApiFunc）のデプロイ

1. `backend/template.yaml` にて ApiFunc を定義
2. Lambda 環境変数に以下を設定
   - `OPENSEARCH_ENDPOINT`
   - `OPENSEARCH_INDEX`
   - `BEDROCK_REGION` など
3. SAM でデプロイ
   ```bash
   cd backend
   sam build
   sam deploy --guided   # 初回のみ
