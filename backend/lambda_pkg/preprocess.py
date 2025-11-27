import re

def split_text_jp(text: str, chunk=900, overlap=150):
    out, i, n = [], 0, len(text)
    while i < n:
        j = min(n, i + chunk)
        out.append(text[i:j])
        i = j - overlap if j < n else j
    return out


def extract_meta(md: str):
    date = re.search(r"date:\s*([0-9\-]+)", md)
    tags = re.findall(r"#(\w+)", md)
    return {"meeting_date": date.group(1) if date else None, "tags": tags}
