import os
import json
import requests

OPENSEARCH_ENDPOINT = os.getenv("OPENSEARCH_ENDPOINT")
INDEX = os.getenv("OPENSEARCH_INDEX", "vendor-notes")

HEADERS = {"Content-Type": "application/json"}

def put_test_doc():
    url = f"{OPENSEARCH_ENDPOINT}/{INDEX}/_doc"  # ← ここ重要: _doc/1 ではない

    body = {
        "text": "これはテストドキュメントです",
        "vector": [0.1, 0.2, 0.3]  # dummy（後で ingest で Bedrock から生成）
    }

    print("Putting test document to create index...")
    print("URL:", url)

    r = requests.post(url, headers=HEADERS, data=json.dumps(body))
    print("Status:", r.status_code)
    print("Response:", r.text)

    r.raise_for_status()

if __name__ == "__main__":
    put_test_doc()
