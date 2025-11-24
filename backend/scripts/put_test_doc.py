import os
import json
import boto3
import requests
from requests_aws4auth import AWS4Auth
import random

# ─────────────────────────────
# 設定
# ─────────────────────────────
REGION = os.getenv("AWS_REGION", "ap-northeast-1")
ENDPOINT = os.environ.get("OPENSEARCH_ENDPOINT", "").rstrip("/")
INDEX_NAME = os.environ.get("OPENSEARCH_INDEX", "vendor-notes")

if not ENDPOINT:
    raise ValueError("OPENSEARCH_ENDPOINT is required")

DOC_URL = f"{ENDPOINT}/{INDEX_NAME}/_doc/1"

# ─────────────────────────────
# SigV4 認証
# ─────────────────────────────
session = boto3.Session()
credentials = session.get_credentials()

if not credentials:
    raise ValueError("AWS credentials not found. Configure AWS credentials first.")

awsauth = AWS4Auth(
    credentials.access_key,
    credentials.secret_key,
    REGION,
    "aoss",
    session_token=credentials.token
)

# ─────────────────────────────
# numpy を使わない 1024 次元ランダムベクトル
# ─────────────────────────────
vec = [random.random() for _ in range(1024)]

# ─────────────────────────────
# mapping + 最初の1件データ
# ─────────────────────────────
payload = {
    "text": "これは OpenSearch Serverless の index 作成テストドキュメントです。",
    "title": "テストタイトル",
    "vector": vec,
    "vendor_name": "テストベンダー",
    "meeting_date": "2024-01-01T00:00:00Z",
    "participants": ["Aさん", "Bさん"],
    "doc_type": "test",
    "tags": ["sample", "test"],

    "mappings": {
        "properties": {
            "text": {"type": "text"},
            "title": {"type": "text"},
            "vector": {
                "type": "knn_vector",
                "dimension": 1024,
                "method": {
                    "name": "hnsw",
                    "space_type": "cosinesimil",
                    "engine": "nmslib",
                    "parameters": {
                        "ef_construction": 512,
                        "m": 16
                    }
                }
            },
            "vendor_name": {"type": "keyword"},
            "meeting_date": {
                "type": "date",
                "format": "strict_date_optional_time||epoch_second"
            },
            "participants": {"type": "keyword"},
            "doc_type": {"type": "keyword"},
            "tags": {"type": "keyword"}
        }
    }
}

# ─────────────────────────────
# PUT 実行
# ─────────────────────────────
def put_test_doc():
    print("Putting test document to create index...")
    print("URL:", DOC_URL)

    headers = {"Content-Type": "application/json"}

    r = requests.put(
        DOC_URL,
        auth=awsauth,
        headers=headers,
        data=json.dumps(payload, ensure_ascii=False)
    )

    print("Status:", r.status_code)
    print("Response:", r.text)

    if r.status_code in (200, 201):
        print("✅ Index created & test document ingested")
    else:
        print("❌ Failed")
        r.raise_for_status()


if __name__ == "__main__":
    put_test_doc()

