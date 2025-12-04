"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { search as apiSearch } from "../../lib/api";
import { SearchBox } from "../../components/search/SearchBox";
import { Filters } from "../../components/search/Filters";
import { ResultCard } from "../../components/search/ResultCard";
import type { SearchFilters, SearchResult } from "../../lib/schemas";

function SearchContent() {
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

export default function SearchPage() {
  return (
    <Suspense fallback={
      <main className="space-y-4">
        <div className="flex gap-2">
          <div className="flex-1 rounded-md border px-3 py-2 bg-gray-100 animate-pulse" />
          <div className="rounded-md border px-4 py-2 bg-gray-100 animate-pulse w-20" />
        </div>
      </main>
    }>
      <SearchContent />
    </Suspense>
  );
}
