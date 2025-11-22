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
