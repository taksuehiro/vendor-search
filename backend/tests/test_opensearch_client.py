from lambda_pkg.opensearch_client import _rrf


def test_rrf_simple():
    a = [{"_id":"A"},{"_id":"B"}]
    b = [{"_id":"B"},{"_id":"C"}]
    fused = _rrf(a,b)
    assert [h["_id"] for h in fused] == ["B","A","C"]
