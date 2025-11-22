import type { SearchResult } from "@/lib/schemas";

export function ResultCard({ result }: { result: SearchResult }) {
  return (
    <article className="rounded-xl border p-4">
      <div className="text-sm text-gray-500">
        {result.meta.vendor_name}空欄{result.meta.meeting_date}
      </div>
      <h3 className="font-medium">{result.title ?? "(無題"}</h3>
      <p className="mt-1 text-sm leading-6 line-clamp-3">{result.snippet ?? result.text}</p>
      {result.tags?.length ? (
        <div className="mt-2 flex flex-wrap gap-1 text-xs">
          {result.tags.map((t) => <span key={t} className="rounded bg-gray-100 px-2 py-0.5">#{t}</span>)}
        </div>
      ) : null}
    </article>
  );
}
