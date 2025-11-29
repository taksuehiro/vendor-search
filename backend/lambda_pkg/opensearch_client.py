import os
import json
import boto3
import requests
from requests_aws4auth import AWS4Auth
from tenacity import retry, stop_after_attempt, wait_fixed

# ==============================
# 環境変数
# ==============================
OS_ENDPOINT = os.environ.get("OPENSEARCH_ENDPOINT", "").rstrip("/")
INDEX_NAME = os.environ.get("OPENSEARCH_INDEX", "vendor-notes-vs")
REGION = os.environ.get("AWS_REGION", "ap-northeast-1")

if not OS_ENDPOINT:
    raise ValueError("OPENSEARCH_ENDPOINT env is required!")

SEARCH_URL = f"{OS_ENDPOINT}/{INDEX_NAME}/_search"

# ==============================
# SigV4 認証（Serverless必須）
# ==============================
session = boto3.Session()
credentials = session.get_credentials()

if not credentials:
    raise ValueError("AWS credentials not found. Configure AWS credentials first.")

awsauth = AWS4Auth(
    credentials.access_key,
    credentials.secret_key,
    REGION,
    "aoss",
    session_token=credentials.token,
)

HEADERS = {"Content-Type": "application/json"}

# ==============================
# Bedrock Embeddings
# ==============================
def embed_query(q: str):
    from .bedrock_client import embed_texts
    return embed_texts([q])[0]

# ==============================
# 検索クライアント
# ==============================

class OpenSearchClient:

    # ---------------------
    # BM25 キーワード検索
    # ---------------------
    @staticmethod
    @retry(reraise=True, stop=stop_after_attempt(3), wait=wait_fixed(0.5))
    def bm25_search(query: str, size: int, filters=None):
        must = [{"multi_match": {"query": query, "fields": ["text^2", "title"]}}]
        if filters:
            must += [{"term": {k: v}} for k, v in filters.items()]

        body = {
            "query": {"bool": {"must": must}},
            "size": size,
        }

        r = requests.post(SEARCH_URL, auth=awsauth, headers=HEADERS,
                          data=json.dumps(body), timeout=10)
        r.raise_for_status()
        return r.json()

    # ---------------------
    # neural kNN（意味検索）
    # ---------------------
    @staticmethod
    @retry(reraise=True, stop=stop_after_attempt(3), wait=wait_fixed(0.5))
    def knn_search(q_vec, size: int, filters=None):

        neural_query = {
            "neural": [
                {
                    "vector": {
                        "query": q_vec,
                        "k": size
                    }
                }
            ]
        }

        if not filters:
            body = {
                "size": size,
                "query": neural_query
            }
        else:
            body = {
                "size": size,
                "query": {
                    "bool": {
                        "filter": [{"term": {k: v}} for k, v in filters.items()],
                        "must": [neural_query]
                    }
                }
            }

        print("DEBUG_BODY:", json.dumps(body)[:500])

        r = requests.post(SEARCH_URL, auth=awsauth, headers=HEADERS,
                          data=json.dumps(body), timeout=10)
        print("DEBUG:", r.text)
        r.raise_for_status()
        return r.json()

    # ---------------------
    # RRF（ランキング融合）
    # ---------------------
    @staticmethod
    def rrf_merge(bm25_resp, knn_resp, size: int, k=60):

        def score(rank):
            return 1.0 / (k + rank + 1)

        scores = {}
        id2doc = {}

        for rank, hit in enumerate(bm25_resp.get("hits", {}).get("hits", [])):
            doc_id = hit["_id"]
            scores.setdefault(doc_id, 0)
            scores[doc_id] += score(rank)
            id2doc[doc_id] = hit

        for rank, hit in enumerate(knn_resp.get("hits", {}).get("hits", [])):
            doc_id = hit["_id"]
            scores.setdefault(doc_id, 0)
            scores[doc_id] += score(rank)
            id2doc.setdefault(doc_id, hit)

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:size]
        return [id2doc[doc_id] for doc_id, _ in ranked]

    # ---------------------
    # ハイブリッド検索
    # ---------------------
    @staticmethod
    def hybrid_search(query: str, size: int = 10, filters=None):

        q_vec = embed_query(query)
        candidate_size = max(50, size * 5)

        bm25_resp = OpenSearchClient.bm25_search(query, candidate_size, filters)
        knn_resp = OpenSearchClient.knn_search(q_vec, candidate_size, filters)

        return OpenSearchClient.rrf_merge(bm25_resp, knn_resp, size)

# ==============================
# ラッパー（互換用）
# ==============================
def search_hybrid(q: str, k=8, filters=None):

    hits = OpenSearchClient.hybrid_search(q, size=k, filters=filters)
    return [
        {
            "id": h["_id"],
            "text": h["_source"].get("text", ""),
            "meta": h["_source"]
        }
        for h in hits
    ]
EOF
