"use client";

import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { search as apiSearch } from "../../lib/api";
import { SearchBox } from "../../components/search/SearchBox";
import { Filters } from "../../components/search/Filters";
import { ResultCard } from "../../components/search/ResultCard";
import type { SearchFilters, SearchResult } from "../../lib/schemas";

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
