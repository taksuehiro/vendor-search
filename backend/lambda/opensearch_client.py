import os, requests
OS = os.environ["OPENSEARCH_ENDPOINT"].rstrip("/")
INDEX = os.environ.get("OPENSEARCH_INDEX_ALIAS", "docs_v_current")
AUTH = (os.environ.get("OS_USER", ""), os.environ.get("OS_PASS", ""))


def _search(body):
    r = requests.post(f"{OS}/{INDEX}/_search", json=body, auth=AUTH, timeout=10)
    r.raise_for_status()
    return r.json()


def _bm25(q, size=50, filters=None):
    must = [{"multi_match": {"query": q, "fields": ["text^2", "title"]}}]
    if filters:
        must += [{"term": {k: v}} for k, v in filters.items()]
    return _search({"size": size, "query": {"bool": {"must": must}}})


def _knn(q_vec, size=50, filters=None):
    body = {"size": size, "knn": {"field": "vector", "query_vector": q_vec, "k": size, "num_candidates": max(100, size)}}
    if filters:
        body["query"] = {"bool": {"filter": [{"term": {k: v}} for k, v in filters.items()]}}
    return _search(body)


def _rrf(list_a, list_b, k=60):
    ranks = {}
    for i, h in enumerate(list_a):
        ranks.setdefault(h["_id"], 0.0)
        ranks[h["_id"]] += 1.0 / (k + i + 1)
    for i, h in enumerate(list_b):
        ranks.setdefault(h["_id"], 0.0)
        ranks[h["_id"]] += 1.0 / (k + i + 1)
    id2doc = {h["_id"]: h for h in list_a + list_b}
    return [id2doc[_id] for _id, _ in sorted(ranks.items(), key=lambda x: x[1], reverse=True)]


def embed_query(q: str):
    from .bedrock_client import embed_texts
    return embed_texts([q])[0]


def search_hybrid(q: str, k=8, filters=None):
    q_vec = embed_query(q)
    bm25 = _bm25(q, size=max(50, k * 5), filters=filters)["hits"]["hits"]
    knn = _knn(q_vec, size=max(50, k * 5), filters=filters)["hits"]["hits"]
    fused = _rrf(bm25, knn)
    return [{"id": h["_id"], "text": h["_source"]["text"], "meta": h["_source"]} for h in fused[:k]]
