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
        placeholder="検索後を入力！"
        className="flex-1 rounded-md border px-3 py-2"
      />
      <button
        onClick={props.onSubmit}
        disabled={props.loading}
        className="rounded-md border px-4 py-2"
      >
        {props.loading ? "検索中..." : "検索"}
      </button>
    </div>
  );
}
