✨ vendor-search プロジェクト AWS 構築の全体像（Serverless 版・改訂版）
0. ゴールとスコープ
🎯 ゴール

STEP1：既存ベンダー情報を検索し回答できるチャットボット基盤を AWS 上に構築

STEP2：議事録（Markdown）を Notion → S3 → Bedrock → OpenSearch Serverless に取り込み、ベクトル検索で高精度検索を実現

🧩 対象コンポーネント

フロントエンド：Amplify（Next.js ホスティング）

バックエンド：API Gateway + Lambda（ApiFunc / IngestFunc）

検索基盤：OpenSearch Serverless

埋め込み / LLM：Amazon Bedrock（Titan Embedding v2、Claude 3 Haiku）

データ保管：S3（Markdown ソース）

1. 準備フェーズ
1-1. 使用リージョン

主に ap-northeast-1

1-2. 命名ルール

S3 バケット：vendor-search-notes-{env}

OpenSearch Serverless コレクション：vendor-notes

Lambda 関数

vendor-search-api-{env}

vendor-search-ingest-{env}

1-3. IAM とセキュリティ方針

Lambda から OpenSearch は IAM 認証（SigV4） を使用

OpenSearch Serverless は以下を作成（必須）

Encryption Policy

Network Policy

Data Access Policy（IAM Principal must include STS セッション ARN）

1-4. ローカル環境

AWS CLI / SAM CLI / Python 3.11

sam build が通る環境

2. バックエンド基盤構築（STEP1）
2-1. OpenSearch Serverless のコレクション作成

コレクション種類：Search（Vector 対応）

名前：vendor-notes

コレクション作成後、3 種のポリシーを設定

📌 必須ポリシー

Encryption Policy（AWSOwnedKey 可）

Network Policy

ダッシュボード利用するので Public Allowed（開発時）

Data Access Policy

Lambda 実行ロール ARN

あなたの AWS SSO ロールの assumed-role / User ARN（STS ARN）
→ 必ず含めないと Dashboard が 401 になる（今回対応済）

2-2. OpenSearch Serverless 用 Index 設計

ベクトル検索対応の mapping（現行ソースに基づく）：

ベクトルフィールド：vector

型：knn_vector

次元：1024（Titan v2）

距離関数：cosinesimil

テキスト：text, title

メタデータ：vendor_name, meeting_date, participants, doc_type, tags

2-3. API Lambda（ApiFunc）
役割

/search?q=xxx を受け取り
→ Bedrock でテキストをベクトル化
→ OpenSearch Serverless で BM25 + kNN + RRF で検索
→ 結果を返す

デプロイ手順
cd backend
sam build
sam deploy --guided

Lambda 環境変数

OPENSEARCH_ENDPOINT

OPENSEARCH_INDEX=vendor-notes

BEDROCK_REGION

AWS_REGION

3. データ更新パイプライン構築（STEP2）
3-1. S3 バケット設計

vendor-search-notes-{env}

キー例：vendors/{vendor_name}/{yyyymmdd}.md

3-2. Ingest Lambda（IngestFunc）
トリガー

S3 の ObjectCreated:*

IAM 権限

S3 GetObject

Bedrock embedding 実行

OpenSearch Serverless HTTP アクセス（IAM SigV4）

処理フロー

S3 イベントから bucket/key を取得

Markdown を取得

900字 + overlap 150字 でチャンク分割

Bedrock Titan v2 で埋め込み生成

メタデータ抽出

OpenSearch Serverless に bulk index

3-3. Notion → S3 連携（任意）

別 Lambda or GitHub Actions で Notion API 経由で Markdown を自動取得

Put 時に IngestFunc が発火し index 更新

4. フロントエンド（Amplify）
4-1. Amplify Hosting

web/ をホスト

build コマンド：

npm ci
npm run build

4-2. API 連携

.env に以下を設定：

NEXT_PUBLIC_API_ENDPOINT=https://xxxx.execute-api.ap-northeast-1.amazonaws.com/Prod


検索時の挙動：

/search?q=xxxxx を叩く

5. 動作確認と運用準備
5-1. 動作確認フロー

S3 に Markdown をアップ

IngestFunc が index に登録

フロントで検索

ApiFunc → Bedrock → OpenSearch → 結果が返る

5-2. モニタリング

Lambda：CloudWatch Logs

Serverless コレクション：Disk 使用量、クエリレイテンシ

Cost Explorer：特に Bedrock / Lambda / Serverless

5-3. セキュリティ調整

本番は VPC へ移動検討

IAM 権限の最小化

dev / prod 環境分離

6. 今後作成する詳細ドキュメント

01_backend_api.md
API Gateway / Lambda / Serverless の構成詳細

02_ingest_pipeline.md
S3 → Lambda → Bedrock → OpenSearch のフロー

03_frontend_amplify.md
Amplify Hosting・Next.js の設定

04_ops_monitoring.md
ログ、モニタリング、アラート、コスト最適化