import json
from unittest.mock import patch
from lambda.app import handler


@patch("lambda.opensearch_client.search_hybrid", return_value=[{"id":"1","text":"dummy","meta":{}}])
@patch("lambda.bedrock_client.generate_answer", return_value=("ok", [{"id":"1","preview":"dummy"}]))
def test_handler_ok(mock_ans, mock_search):
    res = handler({"httpMethod":"GET","queryStringParameters":{"q":"hello"}}, None)
    body = json.loads(res["body"])
    assert res["statusCode"] == 200
    assert body["query"] == "hello"
