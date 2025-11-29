"""
API Lambda Handler
/search?q=xxx を受け取り、OpenSearch + Bedrock で回答生成
"""
import json
import os
from opensearch_client import OpenSearchClient
from bedrock_client import generate_answer


def _response(status, body):
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps(body, ensure_ascii=False)
    }


def handler(event, context):
    """
    API Gateway からのリクエストを処理
    GET /search?q=クエリ文字列
    """
    try:
        # HTTP メソッドチェック
        if event.get("httpMethod") != "GET":
            return _response(405, {"error": "Method not allowed"})
        
        # クエリパラメータ取得
        params = event.get("queryStringParameters") or {}
        query = params.get("q", "").strip()
        
        if not query:
            return _response(400, {"error": "Missing query parameter 'q'"})
        
        # OpenSearch クライアント初期化
        client = OpenSearchClient()
        
        # ハイブリッド検索実行
        size = int(params.get("size", "5"))
        results = client.hybrid_search(query, size=size)
        
        # 結果を整形
        docs = []
        for hit in results:
            docs.append({
                "id": hit["_id"],
                "score": hit["_score"],
                "text": hit["_source"].get("text", ""),
                "meta": {k: v for k, v in hit["_source"].items() if k not in ["text", "vector"]}
            })
        
        # Bedrock で回答生成（オプション）
        if params.get("generate") == "true" and docs:
            answer, citations = generate_answer(query, docs)
            return _response(200, {
                "query": query,
                "answer": answer,
                "citations": citations,
                "results": docs
            })
        
        # 検索結果のみ返す
        return _response(200, {
            "query": query,
            "results": docs
        })
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return _response(500, {"error": str(e)})