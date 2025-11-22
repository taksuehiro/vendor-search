import os, json, boto3, base64, requests
from ..lambda.preprocess import split_text_jp, extract_meta
from ..lambda.bedrock_client import embed_texts

OS = os.environ["OPENSEARCH_ENDPOINT"].rstrip("/")
INDEX = os.environ.get("OPENSEARCH_INDEX_ALIAS", "docs_v_current")
AUTH = (os.environ.get("OS_USER",""), os.environ.get("OS_PASS",""))
s3 = boto3.client("s3")


def handler(event, context):
    # S3 Put 繧､繝吶Φ繝医°繧峨ヰ繧ｱ繝・ヨ/繧ｭ繝ｼ蜿門ｾ・    rec = event["Records"][0]
    bkt = rec["s3"]["bucket"]["name"]
    key = rec["s3"]["object"]["key"]
    body = s3.get_object(Bucket=bkt, Key=key)["Body"].read().decode("utf-8")

    meta = extract_meta(body)
    chunks = split_text_jp(body)
    vecs = embed_texts(chunks)

    docs = []
    for i, (t, v) in enumerate(zip(chunks, vecs)):
        docs.append({"index": {"_index": INDEX}})
        docs.append({"text": t, "vector": v, **meta})

    # bulk
    lines = "\n".join([json.dumps(d, ensure_ascii=False) for d in docs]) + "\n"
    r = requests.post(f"{OS}/_bulk", data=lines.encode("utf-8"), headers={"Content-Type":"application/x-ndjson"}, auth=AUTH, timeout=30)
    r.raise_for_status()
    return {"statusCode": 200, "body": json.dumps({"chunks": len(chunks)})}
