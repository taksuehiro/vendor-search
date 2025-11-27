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
INDEX_NAME = os.environ.get("OPENSEARCH_INDEX", "vendor-notes")
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
    "aoss",  # OpenSearch Serverless のサービス名
    session_token=credentials.token,
)

HEADERS = {"Content-Type": "application/json"}

# ==============================
# ベクトル化（既存の bedrock_client を使用）
# ==============================
def embed_query(q: str):
    from .bedrock_client import embed_texts
    return embed_texts([q])[0]

# ==============================
# kNN / BM25 / RRF クライアント
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

        r = requests.post(SEARCH_URL, auth=awsauth, headers=HEADERS, data=json.dumps(body), timeout=10)
        r.raise_for_status()
        return r.json()

    # ---------------------
    # kNN（意味検索）
    # ---------------------
    @staticmethod
    @retry(reraise=True, stop=stop_after_attempt(3), wait=wait_fixed(0.5))
    def knn_search(q_vec, size: int, filters=None):
        body = {
            "size": size,
            "query": {
                "knn": {
                    "field": "vector",            # ← mapping の vector フィールド名
                    "query_vector": q_vec,        # ← embedding array
                    "k": size                     # ← top-k
                }
            }
        }

        # フィルターがある場合
        if filters:
            body["query"] = {
                "bool": {
                    "filter": [{"term": {k: v}} for k, v in filters.items()],
                    "must": [
                        {
                            "knn": {
                                "field": "vector",
                                "query_vector": q_vec,
                                "k": size
                            }
                        }
                    ]
                }
            }

        r = requests.post(SEARCH_URL, auth=awsauth, headers=HEADERS, data=json.dumps(body), timeout=10)
        r.raise_for_status()
        return r.json()

    # ---------------------
    # RRF（ランキング融合）
    # ---------------------
    @staticmethod
    def rrf_merge(bm25_resp, knn_resp, size: int, k=60):
        """
        RRF (Reciprocal Rank Fusion) で2つの検索結果をマージ
        """
        def score(rank):
            return 1.0 / (k + rank + 1)

        scores = {}
        id2doc = {}

        # BM25 側
        bm25_hits = bm25_resp.get("hits", {}).get("hits", [])
        for rank, hit in enumerate(bm25_hits):
            doc_id = hit["_id"]
            scores[doc_id] = scores.get(doc_id, 0.0) + score(rank)
            id2doc[doc_id] = hit

        # kNN 側
        knn_hits = knn_resp.get("hits", {}).get("hits", [])
        for rank, hit in enumerate(knn_hits):
            doc_id = hit["_id"]
            scores[doc_id] = scores.get(doc_id, 0.0) + score(rank)
            if doc_id not in id2doc:
                id2doc[doc_id] = hit

        # スコア順にソートして上位 n 件を返す
        ranked_ids = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:size]
        return [id2doc[doc_id] for doc_id, _ in ranked_ids]

    # ---------------------
    # ハイブリッド検索（BM25 + kNN + RRF）
    # ---------------------
    @staticmethod
    def hybrid_search(query: str, size: int = 10, filters=None):
        """
        ハイブリッド検索: BM25 + kNN → RRF でマージ
        
        Args:
            query: 検索クエリ文字列
            size: 返す結果数
            filters: フィルター辞書（例: {"vendor_name": "テストベンダー"}）
        
        Returns:
            検索結果のリスト（_source を含む）
        """
        # ベクトル化
        q_vec = embed_query(query)

        # 2つの検索を実行（より多くの候補を取得してから RRF）
        candidate_size = max(50, size * 5)
        bm25_resp = OpenSearchClient.bm25_search(query, candidate_size, filters)
        knn_resp = OpenSearchClient.knn_search(q_vec, candidate_size, filters)

        # RRF マージ
        return OpenSearchClient.rrf_merge(bm25_resp, knn_resp, size)

# ==============================
# 既存の関数インターフェース（後方互換性のため）
# ==============================
def search_hybrid(q: str, k=8, filters=None):
    """
    既存の search_hybrid 関数との互換性を保つラッパー
    
    Args:
        q: 検索クエリ文字列
        k: 返す結果数
        filters: フィルター辞書
    
    Returns:
        [{"id": str, "text": str, "meta": dict}, ...]
    """
    hits = OpenSearchClient.hybrid_search(q, size=k, filters=filters)
    return [
        {
            "id": h["_id"],
            "text": h["_source"].get("text", ""),
            "meta": h["_source"]
        }
        for h in hits
    ]
