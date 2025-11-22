import os, hashlib, boto3, pathlib
s3 = boto3.client("s3")
BUCKET = os.environ["S3_BUCKET_NAME"]
PREFIX = os.getenv("S3_PREFIX","raw/")


def put(path: str):
    b = pathlib.Path(path).read_bytes()
    key = f"{PREFIX}{hashlib.sha256(b).hexdigest()}.md"
    s3.put_object(Bucket=BUCKET, Key=key, Body=b, ContentType="text/markdown")
    return key


if __name__ == "__main__":
    print(put("samples/sample.md"))
