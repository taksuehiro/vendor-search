import os, requests
OS = os.environ["OPENSEARCH_ENDPOINT"].rstrip("/")
INDEX = os.environ.get("OPENSEARCH_INDEX", "docs_v1")
ALIAS = os.environ.get("OPENSEARCH_INDEX_ALIAS", "docs_v_current")
AUTH = (os.getenv("OS_USER",""), os.getenv("OS_PASS",""))

mapping = {
  "settings": {"index": {"knn": True}},
  "mappings": {"properties": {
    "text": {"type":"text"},
    "title":{"type":"text"},
    "vector":{"type":"knn_vector","dimension":1024,"method":{"name":"hnsw","space_type":"cosinesimil"}},
    "vendor_name":{"type":"keyword"},
    "meeting_date":{"type":"date"},
    "participants":{"type":"keyword"},
    "doc_type":{"type":"keyword"},
    "tags":{"type":"keyword"}
  }}
}


def main():
    r = requests.put(f"{OS}/{INDEX}", json=mapping, auth=AUTH)
    if r.status_code not in (200,201) and r.status_code != 400:
        r.raise_for_status()
    requests.post(f"{OS}/_aliases", json={"actions":[
        {"remove":{"index":"*","alias":ALIAS}},
        {"add":{"index":INDEX,"alias":ALIAS}}
    ]}, auth=AUTH).raise_for_status()


if __name__ == "__main__":
    main()
