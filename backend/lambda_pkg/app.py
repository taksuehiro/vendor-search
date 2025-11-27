import json
from .opensearch_client import search_hybrid
from .bedrock_client import generate_answer


def _response(status, body):
    return {"statusCode": status, "headers": {"Content-Type": "application/json"}, "body": json.dumps(body, ensure_ascii=False)}


def handler(event, context):
    try:
        if event.get("httpMethod") != "GET":
            return _response(405, {"error": "Method not allowed"})
        q = (event.get("queryStringParameters") or {}).get("q", "").strip()
        if not q:
            return _response(400, {"error": "missing q"})

        docs = search_hybrid(q, k=8, filters={})
        answer, citations = generate_answer(q, docs)
        return _response(200, {"query": q, "results": [{"id": d["id"], "text": d["text"], "meta": d["meta"]} for d in docs]})
    except Exception as e:
        return _response(500, {"error": str(e)})
