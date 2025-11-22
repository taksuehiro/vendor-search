TTCDX RAG STEP2 — 実装指示書（Cursor向け）

このドキュメントは、スライド「STEP2（RAG社内検索）」の意図をそのままコード化するための実装指示です。
フロントエンド（Next.js）＋バックエンド（AWS SAM: Lambda + Bedrock + OpenSearch）を、フォルダ構成／ファイル構成／各ファイル中身まで具体的に記します。

構想1106

0. 目的（要約）

社内の「ベンダー基本情報・議事録・進捗資料」などを横断検索して意思決定を支援するRAG。

ハイブリッド検索（BM25＋ベクトル）、Bedrock Titan v2で埋め込み、Claude 3 Haikuで要約生成。

構想1106

1. 技術スタック（確定）

Frontend: Next.js 14 / React 18 / Tailwind / Zod /（任意で shadcn/ui）

Backend: AWS SAM / Lambda（Python 3.11）/ OpenSearch / Bedrock(Runtime)

検索戦略: OpenSearchで BM25 と kNN を行い RRF でスコア融合（requests直呼び）。

構想1106

2. リポジトリ構成（作成手順）
project-root/
├─ web/                        # Next.js フロントエンド
└─ backend/                    # SAM（Lambda + Scripts + Tests）


以下の「web/」「backend/」以下を、そのまま同名ファイルで作成してください。

3. Frontend: web/（Next.js 14 App Router）
3.1 目的

トップ（導線）＋検索ページのミニマルUI。

GET /search?q= でJSON取得（SSE可）／URLにクエリ保持。

構想1106

3.2 フォルダ構成
web/
├─ package.json
├─ next.config.mjs
├─ tsconfig.json
├─ postcss.config.mjs
├─ tailwind.config.ts
├─ .eslintrc.cjs                # 任意
├─ .env.local                   # NEXT_PUBLIC_API_BASE_URL=(絶対URL)
├─ app/
│  ├─ layout.tsx
│  ├─ page.tsx
│  └─ search/
│     └─ page.tsx
├─ components/
│  ├─ search/
│  │  ├─ SearchBox.tsx
│  │  ├─ Filters.tsx
│  │  └─ ResultCard.tsx
│  ├─ ui/                       # （shadcn生成物。必要に応じて）
│  └─ common/ThemeToggle.tsx
├─ lib/
│  ├─ api.ts
│  ├─ schemas.ts
│  └─ types/
│     └─ openapi.d.ts           # openapi-typescript で自動生成（任意）
└─ styles/globals.css


構成はスライドの「フロントエンド主要ファイル」に一致させています。

構想1106

3.3 ファイル内容

web/package.json

{
  "name": "ttcdx-rag-web",
  "private": true,
  "scripts": {
    "dev": "next dev -p 3000",
    "build": "next build",
    "start": "next start -p 3000",
    "lint": "next lint",
    "typecheck": "tsc --noEmit"
  },
  "dependencies": {
    "next": "14.2.5",
    "react": "18.3.1",
    "react-dom": "18.3.1",
    "next-themes": "^0.3.0",
    "zod": "^3.23.8"
  },
  "devDependencies": {
    "typescript": "^5.6.2",
    "tailwindcss": "^3.4.10",
    "postcss": "^8.4.41",
    "autoprefixer": "^10.4.20",
    "@types/node": "^20.12.12",
    "@types/react": "^18.3.3",
    "@types/react-dom": "^18.3.0"
  }
}


web/next.config.mjs

/** @type {import('next').NextConfig} */
const nextConfig = { reactStrictMode: true };
export default nextConfig;


web/tsconfig.json

{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["dom", "dom.iterable", "es2022"],
    "allowJs": false,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "types": ["node"]
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx"]
}


web/postcss.config.mjs

export default { plugins: { tailwindcss: {}, autoprefixer: {} } };


web/tailwind.config.ts

import type { Config } from "tailwindcss";
export default {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: { extend: {} },
  plugins: []
} satisfies Config;


web/styles/globals.css

@tailwind base;
@tailwind components;
@tailwind utilities;


web/.env.local（例）

NEXT_PUBLIC_API_BASE_URL=https://<api-id>.execute-api.ap-northeast-1.amazonaws.com/prod


NEXT_PUBLIC_* は公開値。秘密は載せない。

構想1106

web/app/layout.tsx

import "./../styles/globals.css";
import { ThemeProvider } from "next-themes";
import type { ReactNode } from "react";

export const metadata = { title: "TTCDX Knowledge Search" };

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ja" suppressHydrationWarning>
      <body className="min-h-screen">
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
          <div className="max-w-4xl mx-auto p-4">{children}</div>
        </ThemeProvider>
      </body>
    </html>
  );
}


web/app/page.tsx

import Link from "next/link";

export default function Page() {
  return (
    <main className="space-y-6">
      <h1 className="text-2xl font-semibold">Knowledge Search</h1>
      <p className="text-gray-600">議事録やベンダー資料を横断検索</p>
      <Link className="underline" href="/search">検索ページへ</Link>
    </main>
  );
}


web/app/search/page.tsx

"use client";

import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { search as apiSearch } from "@/lib/api";
import { SearchBox } from "@/components/search/SearchBox";
import { Filters } from "@/components/search/Filters";
import { ResultCard } from "@/components/search/ResultCard";
import type { SearchFilters, SearchResult } from "@/lib/schemas";

export default function SearchPage() {
  const sp = useSearchParams();
  const [q, setQ] = useState(sp.get("q") ?? "");
  const [filters, setFilters] = useState<SearchFilters>({});
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<SearchResult[]>([]);
  const controller = useMemo(() => new AbortController(), [q, JSON.stringify(filters)]);

  useEffect(() => {
    const url = new URL(window.location.href);
    url.searchParams.set("q", q);
    window.history.replaceState(null, "", url.toString());
  }, [q]);

  async function doSearch() {
    setLoading(true);
    try {
      const data = await apiSearch({ q, filters, signal: controller.signal });
      setResults(data.results);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="space-y-4">
      <SearchBox value={q} onChange={setQ} onSubmit={doSearch} loading={loading} />
      <Filters value={filters} onChange={setFilters} />
      <div className="space-y-3">
        {results.map((r) => <ResultCard key={r.id} result={r} />)}
      </div>
    </main>
  );
}


web/components/search/SearchBox.tsx

"use client";
import { useCallback } from "react";

export function SearchBox(props: {
  value: string; onChange: (v: string) => void; onSubmit: () => void; loading?: boolean;
}) {
  const onKey = useCallback((e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") props.onSubmit();
  }, [props]);

  return (
    <div className="flex gap-2">
      <input
        value={props.value}
        onChange={(e) => props.onChange(e.target.value)}
        onKeyDown={onKey}
        placeholder="検索語を入力…"
        className="flex-1 rounded-md border px-3 py-2"
      />
      <button
        onClick={props.onSubmit}
        disabled={props.loading}
        className="rounded-md border px-4 py-2"
      >
        {props.loading ? "検索中…" : "検索"}
      </button>
    </div>
  );
}


web/components/search/Filters.tsx

"use client";
import type { SearchFilters } from "@/lib/schemas";

export function Filters({ value, onChange }: {
  value: SearchFilters; onChange: (v: SearchFilters) => void;
}) {
  return (
    <div className="flex gap-2 text-sm">
      <input
        placeholder="ベンダー名"
        className="rounded-md border px-2 py-1"
        value={value.vendor ?? ""}
        onChange={(e) => onChange({ ...value, vendor: e.target.value || undefined })}
      />
      <input
        type="date"
        className="rounded-md border px-2 py-1"
        value={value.from ?? ""}
        onChange={(e) => onChange({ ...value, from: e.target.value || undefined })}
      />
      <input
        type="date"
        className="rounded-md border px-2 py-1"
        value={value.to ?? ""}
        onChange={(e) => onChange({ ...value, to: e.target.value || undefined })}
      />
    </div>
  );
}


web/components/search/ResultCard.tsx

import type { SearchResult } from "@/lib/schemas";

export function ResultCard({ result }: { result: SearchResult }) {
  return (
    <article className="rounded-xl border p-4">
      <div className="text-sm text-gray-500">
        {result.meta.vendor_name}・{result.meta.meeting_date}
      </div>
      <h3 className="font-medium">{result.title ?? "(無題)"}</h3>
      <p className="mt-1 text-sm leading-6 line-clamp-3">{result.snippet ?? result.text}</p>
      {result.tags?.length ? (
        <div className="mt-2 flex flex-wrap gap-1 text-xs">
          {result.tags.map((t) => <span key={t} className="rounded bg-gray-100 px-2 py-0.5">#{t}</span>)}
        </div>
      ) : null}
    </article>
  );
}


web/components/common/ThemeToggle.tsx

"use client";
import { useTheme } from "next-themes";
export function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  return (
    <button
      className="rounded-md border px-2 py-1 text-sm"
      onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
    >
      {theme === "dark" ? "☀︎ Light" : "🌙 Dark"}
    </button>
  );
}


web/lib/schemas.ts

import { z } from "zod";

export const SearchResult = z.object({
  id: z.string(),
  title: z.string().optional(),
  text: z.string(),
  snippet: z.string().optional(),
  tags: z.array(z.string()).optional(),
  meta: z.object({
    vendor_name: z.string().optional(),
    meeting_date: z.string().optional(),
    doc_type: z.string().optional()
  }).passthrough()
});
export type SearchResult = z.infer<typeof SearchResult>;

export const SearchResponse = z.object({
  query: z.string(),
  results: z.array(SearchResult)
});
export type SearchResponse = z.infer<typeof SearchResponse>;

export type SearchFilters = { vendor?: string; from?: string; to?: string; };


web/lib/api.ts

import { SearchFilters, SearchResponse } from "./schemas";

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

function withTimeout(signal: AbortSignal | undefined, ms = 15000): AbortSignal | undefined {
  if (!signal) return undefined;
  const ctrl = new AbortController();
  const id = setTimeout(() => ctrl.abort(), ms);
  (signal as any).addEventListener?.("abort", () => ctrl.abort());
  return ctrl.signal;
}

export async function search(args: {
  q: string; filters?: SearchFilters; signal?: AbortSignal;
}): Promise<SearchResponse> {
  const params = new URLSearchParams({ q: args.q });
  const url = `${BASE}/search?${params.toString()}`;
  const res = await fetch(url, {
    method: "GET",
    signal: withTimeout(args.signal),
    headers: { "Accept": "application/json" }
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

4. Backend: backend/（AWS SAM, Python）
4.1 目的

API Lambda: /search でハイブリッド検索→Claude要約

取り込みLambda（任意）: S3 PUTで起動→前処理→埋め込み→OpenSearch投入（最低限の骨組み）

OpenSearch初期化スクリプト／E2E疎通スクリプトを同梱。

構想1106

4.2 フォルダ構成
backend/
├─ lambda/
│  ├─ app.py
│  ├─ opensearch_client.py
│  ├─ bedrock_client.py
│  ├─ preprocess.py
│  └─ __init__.py
├─ ingest/                      # 取り込みLambda（任意・S3トリガ）
│  └─ app.py
├─ tests/
│  ├─ test_app.py
│  ├─ test_opensearch_client.py
│  └─ test_bedrock_client.py
├─ scripts/
│  ├─ create_index.py
│  ├─ upload_s3_data.py
│  ├─ deploy_lambda.sh
│  └─ invoke_lambda.py
├─ template.yaml
├─ requirements.txt
├─ README.md
└─ .gitignore

4.3 ファイル内容

backend/requirements.txt

boto3
requests


backend/lambda/app.py

import json
from .opensearch_client import search_hybrid
from .bedrock_client import generate_answer

def _response(status, body):
    return {"statusCode": status, "headers": {"Content-Type": "application/json"}, "body": json.dumps(body, ensure_ascii=False)}

def handler(event, context):
    try:
        if event.get("httpMethod") != "GET":
            return _response(405, {"error": "Method not allowed"})
        q = (event.get("queryStringParameters") or {}).get("q", "").strip()
        if not q:
            return _response(400, {"error": "missing q"})

        docs = search_hybrid(q, k=8, filters={})
        answer, citations = generate_answer(q, docs)
        return _response(200, {"query": q, "results": [{"id": d["id"], "text": d["text"], "meta": d["meta"]} for d in docs]})
    except Exception as e:
        return _response(500, {"error": str(e)})


backend/lambda/opensearch_client.py

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
        ranks.setdefault(h["_id"], 0.0); ranks[h["_id"]] += 1.0 / (k + i + 1)
    for i, h in enumerate(list_b):
        ranks.setdefault(h["_id"], 0.0); ranks[h["_id"]] += 1.0 / (k + i + 1)
    id2doc = {h["_id"]: h for h in list_a + list_b}
    return [id2doc[_id] for _id, _ in sorted(ranks.items(), key=lambda x: x[1], reverse=True)]

def embed_query(q: str):
    from .bedrock_client import embed_texts
    return embed_texts([q])[0]

def search_hybrid(q: str, k=8, filters=None):
    q_vec = embed_query(q)
    bm25 = _bm25(q, size=max(50, k * 5), filters=filters)["hits"]["hits"]
    knn  = _knn(q_vec, size=max(50, k * 5), filters=filters)["hits"]["hits"]
    fused = _rrf(bm25, knn)
    return [{"id": h["_id"], "text": h["_source"]["text"], "meta": h["_source"]} for h in fused[:k]]


backend/lambda/bedrock_client.py

import os, json, boto3
BEDROCK = boto3.client("bedrock-runtime", region_name=os.getenv("AWS_REGION", "ap-northeast-1"))
EMBED_MODEL = os.getenv("BEDROCK_EMBEDDINGS_MODEL_ID", "amazon.titan-embed-text-v2:0")  # :0 必須
LLM_MODEL   = os.getenv("LLM_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")

def embed_texts(texts: list[str]) -> list[list[float]]:
    body = {"inputText": texts[0]} if len(texts) == 1 else {"inputText": texts}
    resp = BEDROCK.invoke_model(modelId=EMBED_MODEL, body=json.dumps(body))
    payload = json.loads(resp["body"].read())
    vectors = payload.get("embedding") or payload.get("embeddings")
    return vectors if isinstance(vectors[0], list) else [vectors]

def generate_answer(query: str, docs: list[dict]) -> tuple[str, list[dict]]:
    context = "\n\n".join([f"- {d['text']}" for d in docs])
    prompt = f"以下のコンテキストのみを根拠に日本語で簡潔に回答。根拠が乏しければ『わからない』と答える。\n\n質問:{query}\n\nコンテキスト:\n{context}"
    body = {"anthropic_version":"bedrock-2023-05-31","max_tokens":512,"messages":[{"role":"user","content":[{"type":"text","text":prompt}]}]}
    resp = BEDROCK.invoke_model(modelId=LLM_MODEL, body=json.dumps(body))
    out = json.loads(resp["body"].read())
    answer = out["content"][0]["text"]
    citations = [{"id": d["id"], "preview": d["text"][:140]} for d in docs]
    return answer, citations


backend/lambda/preprocess.py

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


backend/ingest/app.py（S3トリガ取り込み：最小例）

import os, json, boto3, base64, requests
from ..lambda.preprocess import split_text_jp, extract_meta
from ..lambda.bedrock_client import embed_texts

OS = os.environ["OPENSEARCH_ENDPOINT"].rstrip("/")
INDEX = os.environ.get("OPENSEARCH_INDEX_ALIAS", "docs_v_current")
AUTH = (os.environ.get("OS_USER",""), os.environ.get("OS_PASS",""))
s3 = boto3.client("s3")

def handler(event, context):
    # S3 Put イベントからバケット/キー取得
    rec = event["Records"][0]
    bkt = rec["s3"]["bucket"]["name"]; key = rec["s3"]["object"]["key"]
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


backend/tests/test_app.py

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


backend/tests/test_opensearch_client.py

from lambda.opensearch_client import _rrf
def test_rrf_simple():
    a = [{"_id":"A"},{"_id":"B"}]; b = [{"_id":"B"},{"_id":"C"}]
    fused = _rrf(a,b)
    assert [h["_id"] for h in fused] == ["B","A","C"]


backend/tests/test_bedrock_client.py

from unittest.mock import patch
from lambda import bedrock_client as bc

@patch.object(bc.BEDROCK, "invoke_model")
def test_embed_if(mock_invoke):
    mock_invoke.return_value = type("R",(),{"body":type("B",(),{"read":lambda s: b'{"embedding":[[0.1,0.2]]}'})()})
    vec = bc.embed_texts(["hi"])
    assert len(vec[0]) == 2


backend/scripts/create_index.py

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
    if r.status_code not in (200,201) and r.status_code != 400: r.raise_for_status()
    requests.post(f"{OS}/_aliases", json={"actions":[
        {"remove":{"index":"*","alias":ALIAS}},
        {"add":{"index":INDEX,"alias":ALIAS}}
    ]}, auth=AUTH).raise_for_status()

if __name__ == "__main__":
    main()


backend/scripts/upload_s3_data.py

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


backend/scripts/deploy_lambda.sh

#!/usr/bin/env bash
set -euo pipefail
sam build
sam deploy --stack-name rag-step2 --resolve-s3 --capabilities CAPABILITY_IAM


backend/scripts/invoke_lambda.py

import os, json, boto3
fn = os.environ["LAMBDA_FUNCTION_NAME"]
res = boto3.client("lambda").invoke(
  FunctionName=fn,
  Payload=json.dumps({"httpMethod":"GET","queryStringParameters":{"q":"テスト"}})
)
print(res["StatusCode"], res.get("FunctionError"))
print(res["Payload"].read().decode())


backend/template.yaml（SAM, 2つのLambda）

AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31
Description: RAG Step2 backend (Lambda + Bedrock + OpenSearch)

Parameters:
  OpenSearchEndpoint: { Type: String }
  OpenSearchIndexAlias: { Type: String, Default: docs_v_current }
  BedrockEmbeddingsModelId: { Type: String, Default: amazon.titan-embed-text-v2:0 }
  LlmModelId: { Type: String, Default: anthropic.claude-3-haiku-20240307-v1:0 }
  IngestBucketName: { Type: String }

Globals:
  Function:
    Runtime: python3.11
    Timeout: 20
    MemorySize: 1024
    Environment:
      Variables:
        OPENSEARCH_ENDPOINT: !Ref OpenSearchEndpoint
        OPENSEARCH_INDEX_ALIAS: !Ref OpenSearchIndexAlias
        BEDROCK_EMBEDDINGS_MODEL_ID: !Ref BedrockEmbeddingsModelId
        LLM_MODEL_ID: !Ref LlmModelId

Resources:
  ApiFunc:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: lambda/
      Handler: app.handler
      Policies:
        - AWSLambdaBasicExecutionRole
        - Statement:
            - Effect: Allow
              Action: ["bedrock:InvokeModel","bedrock:InvokeModelWithResponseStream"]
              Resource: "*"

  IngestFunc:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: ingest/
      Handler: app.handler
      Events:
        S3Put:
          Type: S3
          Properties:
            Bucket: !Ref IngestBucketName
            Events: s3:ObjectCreated:Put
      Policies:
        - AWSLambdaBasicExecutionRole
        - Statement:
            - Effect: Allow
              Action: ["bedrock:InvokeModel"]
              Resource: "*"
        - S3ReadPolicy:
            BucketName: !Ref IngestBucketName


backend/README.md

# Backend Quickstart

## Setup
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

## OpenSearch index
export OPENSEARCH_ENDPOINT="https://<os-domain>"
python scripts/create_index.py

## Deploy (SAM)
./scripts/deploy_lambda.sh

## E2E
export LAMBDA_FUNCTION_NAME="<ApiFunc name>"
python scripts/invoke_lambda.py


.gitignore

.venv/
__pycache__/
*.pyc
.env
.sam/

5. 開発・動作の手順（要点）

OpenSearch：scripts/create_index.py で docs_v_current を初期化（1024次元 / cosine / HNSW）。

取り込み（任意）：upload_s3_data.py でMarkdownを S3 へ→ ingest Lambda が分割→埋め込み→OpenSearch投入。

API：/search?q=... で BM25＋kNN→RRF→結果JSON。

Web：.env.local の NEXT_PUBLIC_API_BASE_URL をAPI Gatewayの絶対URLに設定→ npm run dev。

構想1106

6. 補足（カスタマイズ指針）

認証：必要に応じ web/lib/api.ts にトークン付与・CORS設定を追加。

SSE：経路が許す場合は streamSearch を有効化。不可なら通常JSONで運用。

構想1106

型の単一ソース：OpenAPI → openapi.d.ts 自動生成 or schemas.ts を基準に。

