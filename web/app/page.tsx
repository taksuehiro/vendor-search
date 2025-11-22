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
