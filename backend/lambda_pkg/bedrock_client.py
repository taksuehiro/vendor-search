"""
Bedrock クライアント
- Titan Embedding v2 でベクトル化
- Claude 3 Haiku で RAG 回答生成
"""
import os
import json
import boto3

BEDROCK = boto3.client("bedrock-runtime", region_name=os.getenv("AWS_REGION", "ap-northeast-1"))
EMBED_MODEL = os.getenv("BEDROCK_EMBEDDINGS_MODEL_ID", "amazon.titan-embed-text-v2:0")
LLM_MODEL = os.getenv("LLM_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")


def embed_text(text: str) -> list[float]:
    """
    単一テキストをベクトル化（Titan Embedding v2）
    
    Args:
        text: 埋め込み対象のテキスト
    
    Returns:
        1024次元のベクトル
    """
    body = {
        "inputText": text,
        "dimensions": 1024,
        "normalize": True
    }
    
    response = BEDROCK.invoke_model(
        modelId=EMBED_MODEL,
        body=json.dumps(body)
    )
    
    result = json.loads(response["body"].read())
    return result["embedding"]


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    複数テキストをベクトル化
    
    Args:
        texts: 埋め込み対象のテキストリスト
    
    Returns:
        ベクトルのリスト
    """
    return [embed_text(t) for t in texts]


def generate_answer(query: str, docs: list[dict]) -> tuple[str, list[dict]]:
    """
    検索結果を元に Claude で回答生成（RAG）
    
    Args:
        query: ユーザーの質問
        docs: 検索結果のリスト
    
    Returns:
        (回答テキスト, 引用情報のリスト)
    """
    # コンテキスト作成
    context_parts = []
    for i, doc in enumerate(docs, 1):
        text = doc.get("text", "")
        context_parts.append(f"[ドキュメント {i}]\n{text}")
    
    context = "\n\n".join(context_parts)
    
    # プロンプト作成
    prompt = f"""以下のコンテキストのみを参照して、質問に日本語で簡潔に回答してください。
コンテキストに情報がない場合は「わからない」と答えてください。

質問: {query}

コンテキスト:
{context}

回答:"""
    
    # Claude 呼び出し
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "messages": [
            {
                "role": "user",
                "content": [{"type": "text", "text": prompt}]
            }
        ]
    }
    
    response = BEDROCK.invoke_model(
        modelId=LLM_MODEL,
        body=json.dumps(body)
    )
    
    result = json.loads(response["body"].read())
    answer = result["content"][0]["text"]
    
    # 引用情報
    citations = [
        {
            "id": doc["id"],
            "score": doc.get("score", 0),
            "preview": doc["text"][:150] + "..." if len(doc["text"]) > 150 else doc["text"]
        }
        for doc in docs[:3]  # 上位3件のみ
    ]
    
    return answer, citations