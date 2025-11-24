import os
import json
import boto3
import requests
from requests_aws4auth import AWS4Auth

# ==============================
# 設定
# ==============================
REGION = os.getenv("AWS_REGION", "ap-northeast-1")
ENDPOINT = os.environ.get("OPENSEARCH_ENDPOINT", "").rstrip("/")
INDEX_NAME = os.environ.get("OPENSEARCH_INDEX", "vendor-notes")
ALIAS = os.environ.get("OPENSEARCH_INDEX_ALIAS", "docs_v_current")

if not ENDPOINT:
    raise ValueError("OPENSEARCH_ENDPOINT environment variable is required")

# OpenSearch Serverless のエンドポイントパス（/indexes/ が必須）
INDEX_URL = f"{ENDPOINT}/indexes/{INDEX_NAME}"

# ==============================
# SigV4 認証 (IAM)
# ==============================
session = boto3.Session()
credentials = session.get_credentials()

if not credentials:
    raise ValueError("AWS credentials not found. Configure AWS credentials first.")

awsauth = AWS4Auth(
    credentials.access_key,
    credentials.secret_key,
    REGION,
    "aoss",  # OpenSearch Serverless のサービス名
    session_token=credentials.token
)

# ==============================
# Index の Mapping 定義
# ==============================
mapping = {
    "settings": {
        "index": {
            "knn": True,
            "knn.algo_param.ef_search": 80  # 検索時の候補数
        }
    },
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
                        "ef_construction": 512,  # 構築時の候補数
                        "m": 16                   # 各ノードの接続数
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

# ==============================
# Index 作成
# ==============================
def create_index():
    print(f"Creating index: {INDEX_NAME}")
    print(f"Endpoint: {ENDPOINT}")
    print(f"URL: {INDEX_URL}")
    print(f"Region: {REGION}")

    headers = {"Content-Type": "application/json"}

    try:
        response = requests.put(
            INDEX_URL,
            auth=awsauth,
            headers=headers,
            data=json.dumps(mapping, ensure_ascii=False)
        )

        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")

        if response.status_code in (200, 201):
            print("✅ Index created successfully")
        elif response.status_code == 400:
            # インデックスが既に存在する場合
            error_body = response.json() if response.text else {}
            if "already exists" in response.text.lower() or "resource_already_exists_exception" in response.text:
                print("⚠️  Index already exists. Skipping creation.")
            else:
                print(f"❌ Index creation failed: {response.text}")
                response.raise_for_status()
        else:
            print(f"❌ Index creation failed with status code {response.status_code}")
            print(f"Response: {response.text}")
            response.raise_for_status()
            raise SystemExit(1)

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {str(e)}")
        raise SystemExit(1)


if __name__ == "__main__":
    create_index()
