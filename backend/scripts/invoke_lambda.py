import os, json, boto3
fn = os.environ["LAMBDA_FUNCTION_NAME"]
res = boto3.client("lambda").invoke(
  FunctionName=fn,
  Payload=json.dumps({"httpMethod":"GET","queryStringParameters":{"q":"繝・せ繝・}})
)
print(res["StatusCode"], res.get("FunctionError"))
print(res["Payload"].read().decode())
