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
            'aoss',  # OpenSearch Serverless
            session_token=credentials.token
        )
        
        self.base_url = f"https://{self.endpoint}"
    
    # =========================================================================
    # BM25 検索（キーワード検索）
    # =========================================================================
    @retry(**RETRY_CONFIG)
    def bm25_search(
        self,
        query: str,
        size: int = 10,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """
        BM25（キーワード）検索を実行
        
        Args:
            query: 検索クエリ文字列
            size: 取得件数
            filters: フィルタ条件（例: {"term": {"category": "tech"}}）
        
        Returns:
            検索結果のリスト [{"_id": ..., "_score": ..., "_source": {...}}, ...]
        """
        # クエリ本体
        must_clause = [{"match": {"text": query}}]
        
        # フィルタがあれば追加
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
    
    # =========================================================================
    # kNN 検索（ベクトル検索 - neural クエリ）
    # =========================================================================
    @retry(**RETRY_CONFIG)
    def knn_search(
        self,
        query_vector: List[float],
        size: int = 10,
        filters: Optional[Dict] = None,
        vector_field: str = "vector"
    ) -> List[Dict]:
        """
        kNN（ベクトル）検索を実行（AOSS VECTORSEARCH 用 neural クエリ）
        
        Args:
            query_vector: クエリベクトル（例: Bedrock Titan-embed-text-v2:0 の出力）
            size: 取得件数
            filters: フィルタ条件（例: {"term": {"category": "tech"}}）
            vector_field: ベクトルフィールド名（デフォルト: "vector"）
        
        Returns:
            検索結果のリスト [{"_id": ..., "_score": ..., "_source": {...}}, ...]
        """
        # AOSS VECTORSEARCH の neural クエリ構造（シンプル版）
        # field 指定を削除して、フィールド名を直接 neural の下に配置
        body = {
            "query": {
                "neural": {
                    vector_field: {
                        "query_vector": query_vector,
                        "k": size
                    }
                }
            },
            "size": size
        }
        
        # フィルタがあれば bool クエリで併用
        if filters:
            body["query"] = {
                "bool": {
                    "must": [
                        {"neural": {vector_field: {"query_vector": query_vector, "k": size}}}
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
        
        # デバッグ情報を含むエラーハンドリング
        if response.status_code != 200:
            error_detail = {
                "status_code": response.status_code,
                "response_text": response.text,
                "query_body": body,
                "vector_dimensions": len(query_vector)
            }
            print(f"kNN Search Error: {json.dumps(error_detail, indent=2, ensure_ascii=False)}")
        
        response.raise_for_status()
        
        result = response.json()
        return result.get('hits', {}).get('hits', [])
    
    # =========================================================================
    # RRF マージ（Reciprocal Rank Fusion）
    # =========================================================================
    @staticmethod
    def rrf_merge(
        bm25_results: List[Dict],
        knn_results: List[Dict],
        k: int = 60
    ) -> List[Dict]:
        """
        BM25 と kNN の結果を RRF でマージ
        
        Args:
            bm25_results: BM25検索結果
            knn_results: kNN検索結果
            k: RRFパラメータ（デフォルト60）
        
        Returns:
            RRFスコアでソートされた結果リスト
        """
        scores = {}
        
        # BM25 結果のスコア計算
        for rank, hit in enumerate(bm25_results, start=1):
            doc_id = hit['_id']
            scores[doc_id] = scores.get(doc_id, 0) + (1.0 / (k + rank))
        
        # kNN 結果のスコア計算
        for rank, hit in enumerate(knn_results, start=1):
            doc_id = hit['_id']
            scores[doc_id] = scores.get(doc_id, 0) + (1.0 / (k + rank))
        
        # 元のドキュメント情報を保持しつつマージ
        doc_map = {}
        for hit in bm25_results + knn_results:
            doc_map[hit['_id']] = hit
        
        # RRFスコアでソート
        merged = []
        for doc_id, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
            doc = doc_map[doc_id].copy()
            doc['_score'] = score  # RRFスコアで上書き
            merged.append(doc)
        
        return merged
    
    # =========================================================================
    # ハイブリッド検索（BM25 + kNN → RRF マージ）
    # =========================================================================
    def hybrid_search(
        self,
        query: str,
        size: int = 10,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """
        ハイブリッド検索を実行（BM25 + kNN を RRF でマージ）
        
        Args:
            query: 検索クエリ文字列
            size: 最終取得件数
            filters: フィルタ条件
        
        Returns:
            RRFマージ後の検索結果
        """
        # 1. クエリをベクトル化（Bedrock Titan-embed-text-v2:0）
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
        
        # 2. BM25 検索（キーワード）
        bm25_results = self.bm25_search(query, size=size*2, filters=filters)
        
        # 3. kNN 検索（ベクトル）
        knn_results = self.knn_search(query_vector, size=size*2, filters=filters)
        
        # 4. RRF マージ
        merged = self.rrf_merge(bm25_results, knn_results)
        
        # 5. 上位 size 件を返す
        return merged[:size]
    
    # =========================================================================
    # ヘルスチェック
    # =========================================================================
    def health_check(self) -> Dict:
        """
        OpenSearch Serverless の接続確認（インデックス存在チェック）
        
        Returns:
            {"status": "ok", "index": "...", "exists": True/False}
        """
        # AOSS では _cluster/health が使えないため、インデックス存在確認を使用
        url = f"{self.base_url}/{self.index_name}"
        
        try:
            response = requests.head(
                url,
                auth=self.auth,
                timeout=10
            )
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


# =========================================================================
# テスト用エントリーポイント
# =========================================================================
if __name__ == "__main__":
    # 環境変数が設定されていることを確認
    client = OpenSearchClient()
    
    # ヘルスチェック
    print("=== Health Check ===")
    print(json.dumps(client.health_check(), indent=2, ensure_ascii=False))
    
    # ハイブリッド検索テスト
    print("\n=== Hybrid Search Test ===")
    results = client.hybrid_search("機械学習", size=3)
    
    for i, hit in enumerate(results, 1):
        print(f"\n[{i}] Score: {hit['_score']:.4f}")
        print(f"ID: {hit['_id']}")
        print(f"Text: {hit['_source'].get('text', '')[:100]}...")