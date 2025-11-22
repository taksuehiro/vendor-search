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
  q: string;
  filters?: SearchFilters;
  signal?: AbortSignal;
}): Promise<SearchResponse> {
  const params = new URLSearchParams({ q: args.q });
  const url = `${BASE}/search?${params.toString()}`;

  const res = await fetch(url, {
    method: "GET",
    signal: withTimeout(args.signal),
    headers: { Accept: "application/json" },
  });

  if (!res.ok) {
    throw new Error(`HTTP error: ${res.status}`);
  }

  return res.json();
}
