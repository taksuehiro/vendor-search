import os, json, boto3
BEDROCK = boto3.client("bedrock-runtime", region_name=os.getenv("AWS_REGION", "ap-northeast-1"))
EMBED_MODEL = os.getenv("BEDROCK_EMBEDDINGS_MODEL_ID", "amazon.titan-embed-text-v2:0")  # :0 蠢・・LLM_MODEL = os.getenv("LLM_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")


def embed_texts(texts: list[str]) -> list[list[float]]:
    body = {"inputText": texts if len(texts) > 1 else texts[0]}

    resp = BEDROCK.invoke_model(modelId=EMBED_MODEL, body=json.dumps(body))

    payload = json.loads(resp["body"].read())



    # Titan v2 の形式に対応

    if "embedding" in payload:

        emb = payload["embedding"]

        # パターンA: {"vector": [...]}

        if isinstance(emb, dict) and "vector" in emb:

            return [emb["vector"]]

        # パターンB: ただの list

        if isinstance(emb, list):

            return [emb]



    # Titan v1系 or embeddings plural 対応

    if "embeddings" in payload:

        emb = payload["embeddings"]

        if isinstance(emb, list) and isinstance(emb[0], dict) and "vector" in emb[0]:

            return [emb[0]["vector"]]

        return emb



    raise ValueError(f"Unexpected embed payload: {payload}")


def generate_answer(query: str, docs: list[dict]) -> tuple[str, list[dict]]:
    context = "\n\n".join([f"- {d['text']}" for d in docs])
    prompt = f"莉･荳九・繧ｳ繝ｳ繝・く繧ｹ繝医・縺ｿ繧呈ｹ諡縺ｫ譌･譛ｬ隱槭〒邁｡貎斐↓蝗樒ｭ斐よｹ諡縺御ｹ上＠縺代ｌ縺ｰ縲弱ｏ縺九ｉ縺ｪ縺・上→遲斐∴繧九・n\n雉ｪ蝠・{query}\n\n繧ｳ繝ｳ繝・く繧ｹ繝・\n{context}"
    body = {"anthropic_version": "bedrock-2023-05-31", "max_tokens": 512, "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}]}
    resp = BEDROCK.invoke_model(modelId=LLM_MODEL, body=json.dumps(body))
    out = json.loads(resp["body"].read())
    answer = out["content"][0]["text"]
    citations = [{"id": d["id"], "preview": d["text"][:140]} for d in docs]
    return answer, citations
