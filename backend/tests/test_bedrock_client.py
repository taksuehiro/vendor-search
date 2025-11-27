from unittest.mock import patch
from lambda_pkg import bedrock_client as bc


@patch.object(bc.BEDROCK, "invoke_model")
def test_embed_if(mock_invoke):
    mock_invoke.return_value = type("R",(),{"body":type("B",(),{"read":lambda s: b'{\"embedding\":[[0.1,0.2]]}'})()})
    vec = bc.embed_texts(["hi"])
    assert len(vec[0]) == 2
