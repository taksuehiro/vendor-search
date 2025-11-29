"""
OpenSearch Serverless (VECTORSEARCH) クライアント
BM25 / kNN / RRF / Hybrid Search 対応
"""
import os
import json
import boto3
from typing import List, Dict, Optional
from requests_aws4auth import AWS4Auth
import requests
from retrying import retry

# リトライ設定：最大3回、2秒間隔
RETRY_CONFIG = {
    'stop_max_attempt_number': 3,
    'wait_fixed': 2000
}


class OpenSearchClient:
    """OpenSearch Serverless VECTORSEARCH コレクション用クライアント"""
    
    def __init__(self):
        """
        環境変数から接続情報を取得し、SigV4認証を初期化
        必要な環境変数:
        - OPENSEARCH_ENDPOINT: AOSSエンドポイント（https://なし）
        - AWS_REGION: リージョン（デフォルト: ap-northeast-1）
        """
        self.endpoint = os.environ.get('OPENSEARCH_ENDPOINT')
        if not self.endpoint:
            raise ValueError("環境変数 OPENSEARCH_ENDPOINT が設定されていません")
        
        # エンドポイント正規化（https:// を除去）
        self.endpoint = self.endpoint.replace('https://', '').replace('http://', '')
        
        self.region = os.environ.get('AWS_REGION', 'ap-northeast-1')
        self.index_name = os.environ.get('OPENSEARCH_INDEX', 'knowledge-base')
        
        # SigV4認証の初期化
        credentials = boto3.Session().get_credentials()
        self.auth = AWS4Auth(
            credentials.access_key,
            credentials.secret_key,
            self.region,
            'aoss',
            session_token=credentials.token
        )
        
        self.base_url = f"https://{self.endpoint}"
    
    @retry(**RETRY_CONFIG)
    def bm25_search(
        self,
        query: str,
        size: int = 10,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """BM25（キーワード）検索を実行"""
        must_clause = [{"match": {"text": query}}]
        
        if filters:
            must_clause.append(filters)
        
        body = {
            "query": {
                "bool": {
                    "must": must_clause
                }
            },
            "size": size
        }
        
        url = f"{self.base_url}/{self.index_name}/_search"
        
        response = requests.post(
            url,
            auth=self.auth,
            headers={"Content-Type": "application/json"},
            json=body,
            timeout=30
        )
        response.raise_for_status()
        
        result = response.json()
        return result.get('hits', {}).get('hits', [])
    
    @retry(**RETRY_CONFIG)
    def knn_search(
        self,
        query_vector: List[float],
        size: int = 10,
        filters: Optional[Dict] = None,
        vector_field: str = "vector"
    ) -> List[Dict]:
        """kNN（ベクトル）検索を実行（AOSS VECTORSEARCH 用）"""
        # AOSS VECTORSEARCH の正しい knn クエリ構造
        body = {
            "query": {
                "knn": {
                    vector_field: {
                        "vector": query_vector,
                        "k": size
                    }
                }
            },
            "size": size
        }
        
        if filters:
            body["query"] = {
                "bool": {
                    "must": [
                        {"knn": {vector_field: {"vector": query_vector, "k": size}}}
                    ],
                    "filter": filters
                }
            }
        
        url = f"{self.base_url}/{self.index_name}/_search"
        
        response = requests.post(
            url,
            auth=self.auth,
            headers={"Content-Type": "application/json"},
            json=body,
            timeout=30
        )
        response.raise_for_status()
        
        result = response.json()
        return result.get('hits', {}).get('hits', [])
    
    @staticmethod
    def rrf_merge(
        bm25_results: List[Dict],
        knn_results: List[Dict],
        k: int = 60
    ) -> List[Dict]:
        """BM25 と kNN の結果を RRF でマージ"""
        scores = {}
        
        for rank, hit in enumerate(bm25_results, start=1):
            doc_id = hit['_id']
            scores[doc_id] = scores.get(doc_id, 0) + (1.0 / (k + rank))
        
        for rank, hit in enumerate(knn_results, start=1):
            doc_id = hit['_id']
            scores[doc_id] = scores.get(doc_id, 0) + (1.0 / (k + rank))
        
        doc_map = {}
        for hit in bm25_results + knn_results:
            doc_map[hit['_id']] = hit
        
        merged = []
        for doc_id, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
            doc = doc_map[doc_id].copy()
            doc['_score'] = score
            merged.append(doc)
        
        return merged
    
    def hybrid_search(
        self,
        query: str,
        size: int = 10,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """ハイブリッド検索を実行（BM25 + kNN → RRF マージ）"""
        bedrock = boto3.client('bedrock-runtime', region_name=self.region)
        
        embed_response = bedrock.invoke_model(
            modelId='amazon.titan-embed-text-v2:0',
            contentType='application/json',
            accept='application/json',
            body=json.dumps({
                "inputText": query,
                "dimensions": 1024,
                "normalize": True
            })
        )
        
        embed_result = json.loads(embed_response['body'].read())
        query_vector = embed_result['embedding']
        
        bm25_results = self.bm25_search(query, size=size*2, filters=filters)
        knn_results = self.knn_search(query_vector, size=size*2, filters=filters)
        
        merged = self.rrf_merge(bm25_results, knn_results)
        
        return merged[:size]
    
    def health_check(self) -> Dict:
        """OpenSearch Serverless の接続確認"""
        url = f"{self.base_url}/{self.index_name}"
        
        try:
            response = requests.head(url, auth=self.auth, timeout=10)
            exists = response.status_code == 200
            
            return {
                "status": "ok" if exists else "index_not_found",
                "index": self.index_name,
                "exists": exists,
                "endpoint": self.endpoint
            }
        except Exception as e:
            return {
                "status": "error",
                "index": self.index_name,
                "error": str(e),
                "endpoint": self.endpoint
            }