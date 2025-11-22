import os, json, boto3
BEDROCK = boto3.client("bedrock-runtime", region_name=os.getenv("AWS_REGION", "ap-northeast-1"))
EMBED_MODEL = os.getenv("BEDROCK_EMBEDDINGS_MODEL_ID", "amazon.titan-embed-text-v2:0")  # :0 蠢・・LLM_MODEL = os.getenv("LLM_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")


def embed_texts(texts: list[str]) -> list[list[float]]:
    body = {"inputText": texts[0]} if len(texts) == 1 else {"inputText": texts}
    resp = BEDROCK.invoke_model(modelId=EMBED_MODEL, body=json.dumps(body))
    payload = json.loads(resp["body"].read())
    vectors = payload.get("embedding") or payload.get("embeddings")
    return vectors if isinstance(vectors[0], list) else [vectors]


def generate_answer(query: str, docs: list[dict]) -> tuple[str, list[dict]]:
    context = "\n\n".join([f"- {d['text']}" for d in docs])
    prompt = f"莉･荳九・繧ｳ繝ｳ繝・く繧ｹ繝医・縺ｿ繧呈ｹ諡縺ｫ譌･譛ｬ隱槭〒邁｡貎斐↓蝗樒ｭ斐よｹ諡縺御ｹ上＠縺代ｌ縺ｰ縲弱ｏ縺九ｉ縺ｪ縺・上→遲斐∴繧九・n\n雉ｪ蝠・{query}\n\n繧ｳ繝ｳ繝・く繧ｹ繝・\n{context}"
    body = {"anthropic_version": "bedrock-2023-05-31", "max_tokens": 512, "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}]}
    resp = BEDROCK.invoke_model(modelId=LLM_MODEL, body=json.dumps(body))
    out = json.loads(resp["body"].read())
    answer = out["content"][0]["text"]
    citations = [{"id": d["id"], "preview": d["text"][:140]} for d in docs]
    return answer, citations
