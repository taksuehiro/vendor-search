"use client";

import { useState } from "react";
import { SearchBox } from "@/components/search/SearchBox";
import { ResultCard } from "@/components/search/ResultCard";
import type { SearchResult } from "@/lib/schemas";

const COMPANIES = [
  "Akari",
  "Acrosstudio",
  "Araya",
  "BrainPad",
  "Eriza",
  "Fusic",
  "LaboroAI",
  "LiberCraft",
  "LightBlue",
  "NUCO",
  "TANREN",
  "Weel",
  "クラスメソッド",
];

type GuidedCriteria = {
  purpose: string | null;
  requirements: string;
  budget: string | null;
  track_record: string | null;
  internal_support: string | null;
  speed: string | null;
  priority: string | null;
};

export default function HomePage() {
  const [query, setQuery] = useState("");
  const [company, setCompany] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [guidedCriteria, setGuidedCriteria] = useState<GuidedCriteria>({
    purpose: null,
    requirements: "",
    budget: null,
    track_record: null,
    internal_support: null,
    speed: null,
    priority: null,
  });

  const handleFreeSearch = async () => {
    if (!query.trim()) {
      alert("検索キーワードを入力してください");
      return;
    }

    setLoading(true);
    // ダミーデータ（実際はAPIコール）
    setTimeout(() => {
      const mockResults = getMockFreeSearchResults(query, company);
      setResults(mockResults);
      setLoading(false);
    }, 500);
  };

  const handleGuidedSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!hasSelection(guidedCriteria)) {
      alert("少なくとも1つの質問に回答してください");
      return;
    }

    setLoading(true);
    // ダミーデータ（実際はAPIコール）
    setTimeout(() => {
      const mockResults = getMockGuidedSearchResults(guidedCriteria);
      setResults(mockResults);
      setLoading(false);
    }, 500);
  };

  const handleReset = () => {
    setQuery("");
    setCompany("");
    setResults([]);
    setGuidedCriteria({
      purpose: null,
      requirements: "",
      budget: null,
      track_record: null,
      internal_support: null,
      speed: null,
      priority: null,
    });
  };

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50">
      {/* 左側: Knowledge Search (60%) */}
      <div className="w-[60%] bg-white border-r border-gray-200 flex flex-col">
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-2xl text-gray-900">🔍 Knowledge Search</h2>
        </div>

        {/* 検索エリア */}
        <div className="p-6 border-b border-gray-200 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              🏢 会社名
            </label>
            <select
              value={company}
              onChange={(e) => setCompany(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">会社名で絞り込む</option>
              {COMPANIES.map((comp) => (
                <option key={comp} value={comp}>
                  {comp}
                </option>
              ))}
            </select>
          </div>

          <div>
            <div className="flex gap-2">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleFreeSearch();
                }}
                placeholder="検索語を入力してください..."
                className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
              <button
                onClick={handleFreeSearch}
                disabled={loading}
                className="px-6 py-2 bg-blue-600 text-white rounded-md font-medium hover:bg-blue-700 transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed"
              >
                検索
              </button>
            </div>
          </div>
        </div>

        {/* 検索結果エリア */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="flex justify-center items-center py-12">
              <div className="w-12 h-12 border-4 border-gray-100 border-t-blue-600 rounded-full animate-spin" />
            </div>
          ) : results.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <p className="mb-2">検索結果がここに表示されます。</p>
              <p className="text-sm">キーワードを入力して検索してください。</p>
            </div>
          ) : (
            <div className="space-y-3">
              {results.map((r) => (
                <ResultCard key={r.id} result={r} />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* 右側: ベンダー選定ガイド (40%) */}
      <div className="w-[40%] bg-white flex flex-col overflow-y-auto">
        <div className="p-6 text-center border-b border-gray-200">
          <span className="text-2xl">🎯</span>
          <h2 className="text-2xl font-bold text-gray-900 mt-2">ベンダー選定ガイド</h2>
          <p className="text-sm text-gray-500 mt-1">
            いくつかの質問に答えて、最適なベンダーを見つけましょう
          </p>
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          <form onSubmit={handleGuidedSearch} className="space-y-5">
            {/* Q1: 案件の目的 */}
            <div className="bg-gray-50 border border-gray-200 rounded-xl p-5">
              <label className="flex items-center gap-2 text-base font-semibold text-gray-900 mb-4">
                <span>❓</span>
                <span>この案件の目的は？</span>
              </label>
              <div className="space-y-3">
                {[
                  { value: "efficiency", label: "業務効率化（コスト削減）" },
                  { value: "new_business", label: "新規事業・サービス開発" },
                  { value: "research", label: "技術検証・PoC" },
                  { value: "training", label: "人材育成・内製化準備" },
                ].map((option) => (
                  <label
                    key={option.value}
                    className="flex items-center gap-3 p-3 bg-white border-2 border-gray-200 rounded-lg cursor-pointer hover:border-blue-500 hover:bg-blue-50 transition-all"
                  >
                    <input
                      type="radio"
                      name="purpose"
                      value={option.value}
                      checked={guidedCriteria.purpose === option.value}
                      onChange={(e) =>
                        setGuidedCriteria({ ...guidedCriteria, purpose: e.target.value })
                      }
                      className="w-5 h-5"
                    />
                    <span className="text-sm text-gray-700">{option.label}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Q2: 具体的な要件 */}
            <div className="bg-gray-50 border border-gray-200 rounded-xl p-5">
              <label className="flex items-center gap-2 text-base font-semibold text-gray-900 mb-4">
                <span>📝</span>
                <span>具体的な要件を教えてください</span>
              </label>
              <textarea
                value={guidedCriteria.requirements}
                onChange={(e) =>
                  setGuidedCriteria({ ...guidedCriteria, requirements: e.target.value })
                }
                placeholder="例：画像認識を使った不良品検知、LLMを活用したチャットボット、社内文書のRAG検索システム など"
                rows={3}
                className="w-full px-3 py-2 border-2 border-gray-200 rounded-lg text-sm focus:outline-none focus:border-blue-500"
              />
              <small className="block mt-2 text-xs text-gray-500">
                ※ この情報はフリー検索にも活用されます
              </small>
            </div>

            {/* Q3: 予算 */}
            <div className="bg-gray-50 border border-gray-200 rounded-xl p-5">
              <label className="flex items-center gap-2 text-base font-semibold text-gray-900 mb-4">
                <span>❓</span>
                <span>予算は？</span>
              </label>
              <div className="space-y-3">
                {[
                  { value: "low", label: "〜500万円" },
                  { value: "medium", label: "500〜2000万円" },
                  { value: "high", label: "2000万円〜" },
                ].map((option) => (
                  <label
                    key={option.value}
                    className="flex items-center gap-3 p-3 bg-white border-2 border-gray-200 rounded-lg cursor-pointer hover:border-blue-500 hover:bg-blue-50 transition-all"
                  >
                    <input
                      type="radio"
                      name="budget"
                      value={option.value}
                      checked={guidedCriteria.budget === option.value}
                      onChange={(e) =>
                        setGuidedCriteria({ ...guidedCriteria, budget: e.target.value })
                      }
                      className="w-5 h-5"
                    />
                    <span className="text-sm text-gray-700">{option.label}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Q4: 実績の重要度 */}
            <div className="bg-gray-50 border border-gray-200 rounded-xl p-5">
              <label className="flex items-center gap-2 text-base font-semibold text-gray-900 mb-4">
                <span>❓</span>
                <span>実績の重要度は？</span>
              </label>
              <div className="space-y-3">
                {[
                  { value: "low", label: "問わない（新しいベンダーでもOK）" },
                  { value: "medium", label: "ある程度の実績は欲しい" },
                  { value: "high", label: "豊富な実績が必須" },
                ].map((option) => (
                  <label
                    key={option.value}
                    className="flex items-center gap-3 p-3 bg-white border-2 border-gray-200 rounded-lg cursor-pointer hover:border-blue-500 hover:bg-blue-50 transition-all"
                  >
                    <input
                      type="radio"
                      name="track_record"
                      value={option.value}
                      checked={guidedCriteria.track_record === option.value}
                      onChange={(e) =>
                        setGuidedCriteria({ ...guidedCriteria, track_record: e.target.value })
                      }
                      className="w-5 h-5"
                    />
                    <span className="text-sm text-gray-700">{option.label}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Q5: 内製化支援 */}
            <div className="bg-gray-50 border border-gray-200 rounded-xl p-5">
              <label className="flex items-center gap-2 text-base font-semibold text-gray-900 mb-4">
                <span>❓</span>
                <span>内製化支援の必要性は？</span>
              </label>
              <div className="space-y-3">
                {[
                  { value: "low", label: "不要（外注でOK）" },
                  { value: "medium", label: "あると嬉しい" },
                  { value: "high", label: "必須（自社で運用したい）" },
                ].map((option) => (
                  <label
                    key={option.value}
                    className="flex items-center gap-3 p-3 bg-white border-2 border-gray-200 rounded-lg cursor-pointer hover:border-blue-500 hover:bg-blue-50 transition-all"
                  >
                    <input
                      type="radio"
                      name="internal_support"
                      value={option.value}
                      checked={guidedCriteria.internal_support === option.value}
                      onChange={(e) =>
                        setGuidedCriteria({ ...guidedCriteria, internal_support: e.target.value })
                      }
                      className="w-5 h-5"
                    />
                    <span className="text-sm text-gray-700">{option.label}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Q6: 開発スピード */}
            <div className="bg-gray-50 border border-gray-200 rounded-xl p-5">
              <label className="flex items-center gap-2 text-base font-semibold text-gray-900 mb-4">
                <span>❓</span>
                <span>開発スピードの重要度は？</span>
              </label>
              <div className="space-y-3">
                {[
                  { value: "high", label: "急ぎ（3ヶ月以内に必要）" },
                  { value: "medium", label: "標準的（6ヶ月程度）" },
                  { value: "low", label: "じっくり取り組みたい（1年以上）" },
                ].map((option) => (
                  <label
                    key={option.value}
                    className="flex items-center gap-3 p-3 bg-white border-2 border-gray-200 rounded-lg cursor-pointer hover:border-blue-500 hover:bg-blue-50 transition-all"
                  >
                    <input
                      type="radio"
                      name="speed"
                      value={option.value}
                      checked={guidedCriteria.speed === option.value}
                      onChange={(e) =>
                        setGuidedCriteria({ ...guidedCriteria, speed: e.target.value })
                      }
                      className="w-5 h-5"
                    />
                    <span className="text-sm text-gray-700">{option.label}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Q7: 重視するポイント */}
            <div className="bg-gray-50 border border-gray-200 rounded-xl p-5">
              <label className="flex items-center gap-2 text-base font-semibold text-gray-900 mb-4">
                <span>❓</span>
                <span>最も重視するポイントは？</span>
              </label>
              <div className="space-y-3">
                {[
                  { value: "cost", label: "コスト（予算を抑えたい）" },
                  { value: "speed", label: "スピード（早く結果が欲しい）" },
                  { value: "quality", label: "品質（技術力の高さ）" },
                  { value: "support", label: "サポート（手厚い支援）" },
                  { value: "track_record", label: "実績（信頼性）" },
                ].map((option) => (
                  <label
                    key={option.value}
                    className="flex items-center gap-3 p-3 bg-white border-2 border-gray-200 rounded-lg cursor-pointer hover:border-blue-500 hover:bg-blue-50 transition-all"
                  >
                    <input
                      type="radio"
                      name="priority"
                      value={option.value}
                      checked={guidedCriteria.priority === option.value}
                      onChange={(e) =>
                        setGuidedCriteria({ ...guidedCriteria, priority: e.target.value })
                      }
                      className="w-5 h-5"
                    />
                    <span className="text-sm text-gray-700">{option.label}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* ボタン */}
            <div className="space-y-3 pt-4 border-t border-gray-200">
              <button
                type="submit"
                className="w-full px-4 py-4 bg-gradient-to-r from-blue-600 to-blue-700 text-white rounded-xl font-semibold hover:from-blue-700 hover:to-blue-800 transition-all shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 flex items-center justify-center gap-2"
              >
                <span>🔍</span>
                <span>深掘りのベクトル検索</span>
              </button>
              <button
                type="button"
                onClick={handleReset}
                className="w-full px-4 py-2 bg-white text-gray-700 border-2 border-gray-300 rounded-lg font-medium hover:bg-gray-50 transition-colors"
              >
                リセット
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

// ユーティリティ関数
function hasSelection(criteria: GuidedCriteria): boolean {
  return Object.values(criteria).some((v) => v !== null && v !== "");
}

// ダミーデータ生成
function getMockFreeSearchResults(
  query: string,
  company: string
): SearchResult[] {
  const companies = COMPANIES;
  const filtered = company
    ? companies.filter((c) => c === company)
    : companies.slice(0, 5);

  return filtered.map((comp, index) => ({
    id: `result-${index}`,
    text: `${query}に関する${comp}のナレッジベースからの検索結果です。実際のプロジェクトでの実績や技術的な知見が含まれています。`,
    title: `${comp} - ${query}に関する情報`,
    snippet: `${query}に関する${comp}のナレッジベースからの検索結果です。`,
    meta: {
      vendor_name: comp,
      meeting_date: new Date().toISOString().split("T")[0],
      doc_type: "議事録",
    },
  }));
}

function getMockGuidedSearchResults(
  criteria: GuidedCriteria
): SearchResult[] {
  const companies = ["LaboroAI", "BrainPad", "NUCO", "LiberCraft", "Akari"];
  return companies.map((comp, index) => ({
    id: `guided-${index}`,
    text: `${comp}は、${criteria.purpose || "様々な"}プロジェクトに強みを持っています。`,
    title: `${comp} - 推薦ベンダー`,
    snippet: `${comp}は、${criteria.purpose || "様々な"}プロジェクトに強みを持っています。`,
    meta: {
      vendor_name: comp,
      meeting_date: new Date().toISOString().split("T")[0],
      doc_type: "推薦",
    },
  }));
}
