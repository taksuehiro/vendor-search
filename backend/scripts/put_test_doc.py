import os
import json
import boto3
import requests
from requests_aws4auth import AWS4Auth
import numpy as np

# ─────────────────────────────
# 設定
# ─────────────────────────────
REGION = os.getenv("AWS_REGION", "ap-northeast-1")
ENDPOINT = os.environ.get("OPENSEARCH_ENDPOINT", "").rstrip("/")
INDEX_NAME = os.environ.get("OPENSEARCH_INDEX", "vendor-notes")

if not ENDPOINT:
    raise ValueError("OPENSEARCH_ENDPOINT is required")

# ★ Serverless の Document API パス：
# PUT https://<endpoint>/<index-name>/_doc/<id>
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
# Test vector（1024次元の乱数）
# ─────────────────────────────
vec = np.random.rand(1024).astype(float).tolist()

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

    # ★ Serverless は "最初の PUT に mapping を含めると index を作成"
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
# 実行
# ─────────────────────────────
def put_test_doc():
    print("Putting test document to create index...")
    print("URL:", DOC_URL)
    print("Index:", INDEX_NAME)
    print("Region:", REGION)

    headers = {"Content-Type": "application/json"}

    try:
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
            raise SystemExit(1)

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {str(e)}")
        raise SystemExit(1)


if __name__ == "__main__":
    put_test_doc()

