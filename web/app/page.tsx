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

interface VendorSearchForm {
  priorities: string[];        // 質問1の複数選択
  developmentStyle: string;    // 質問2の単一選択
  companySize: string;         // 質問3の単一選択
  techStack: string[];         // 質問4の複数選択
  industry: string;            // 質問5の単一選択
  ipOwnership: string;         // 質問6の単一選択
  partnership: string;         // 質問7の単一選択
}

interface VendorRecommendation {
  company_name: string;
  match_score: number;
  reasoning: string;
}

interface RecommendationResponse {
  recommendations: VendorRecommendation[];
}

export default function HomePage() {
  const [query, setQuery] = useState("");
  const [company, setCompany] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [recommendations, setRecommendations] = useState<VendorRecommendation[]>([]);
  const [recommendationLoading, setRecommendationLoading] = useState(false);
  const [recommendationError, setRecommendationError] = useState<string | null>(null);
  const [vendorForm, setVendorForm] = useState<VendorSearchForm>({
    priorities: [],
    developmentStyle: "",
    companySize: "",
    techStack: [],
    industry: "",
    ipOwnership: "",
    partnership: "",
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
    
    if (!hasSelection(vendorForm)) {
      const shouldContinue = window.confirm(
        "より正確な推薦のため、1つ以上選択することをおすすめします。\nこのまま検索を続けますか？"
      );
      if (!shouldContinue) return;
    }

    setRecommendationLoading(true);
    setRecommendationError(null);
    setRecommendations([]);

    try {
      const apiEndpoint = process.env.NEXT_PUBLIC_API_ENDPOINT;
      if (!apiEndpoint) {
        throw new Error("APIエンドポイントが設定されていません");
      }

      // valueを日本語ラベルにマッピング
      const mapValueToLabel = (field: string, value: string): string => {
        const mappings: Record<string, Record<string, string>> = {
          priorities: {
            tech_innovation: "技術的な先進性・最新技術の活用",
            domain_knowledge: "業界知見・ドメイン理解の深さ",
            internalization: "内製化支援・ナレッジ移管",
            aws_development: "AWS環境での開発・運用",
            cost_performance: "コストパフォーマンス",
            implementation_speed: "実装スピード",
          },
          developmentStyle: {
            full_outsource: "完全受託（丸投げOK）",
            collaborative: "協働開発（一緒に作る）",
            internal_support: "内製支援・伴走型（最終的に自社で運用）",
            consulting: "コンサルティング中心（企画・設計まで）",
          },
          companySize: {
            large: "大手・準大手が安心",
            medium: "中堅企業（30-100名程度）",
            small: "小規模でも専門性が高ければ良い（5-20名程度）",
            no_preference: "特にこだわりなし",
          },
          techStack: {
            aws: "AWS（必須）",
            azure_gcp: "Azure/GCP",
            ai_ml: "AI/機械学習",
            modern_web: "モダンWeb技術（React/Vue等）",
            data_analysis: "データ分析基盤",
            none: "特になし",
          },
          industry: {
            manufacturing: "製造業・工場",
            logistics: "物流・サプライチェーン",
            trading: "商社・貿易",
            finance: "金融・保険",
            generic: "汎用的なシステム",
          },
          ipOwnership: {
            full_transfer: "当社に完全譲渡してほしい",
            standard: "標準的な契約で問題ない",
            vendor_keep: "ベンダー側保持でも構わない",
            undecided: "まだ決めていない",
          },
          partnership: {
            one_time: "単発で完結させたい",
            ongoing: "良ければ継続的に依頼したい",
            strategic: "長期的な戦略パートナーを探している",
          },
        };
        return mappings[field]?.[value] || value;
      };

      // APIリクエスト用のデータを準備
      const apiPayload = {
        priorities: vendorForm.priorities.map((v) => mapValueToLabel("priorities", v)),
        developmentStyle: mapValueToLabel("developmentStyle", vendorForm.developmentStyle),
        companySize: mapValueToLabel("companySize", vendorForm.companySize),
        techStack: vendorForm.techStack.map((v) => mapValueToLabel("techStack", v)),
        industry: mapValueToLabel("industry", vendorForm.industry),
        ipOwnership: mapValueToLabel("ipOwnership", vendorForm.ipOwnership),
        partnership: mapValueToLabel("partnership", vendorForm.partnership),
      };

      // APIリクエスト送信
      const response = await fetch(apiEndpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(apiPayload),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
          errorData.error || `APIエラー: ${response.status} ${response.statusText}`
        );
      }

      const data: RecommendationResponse = await response.json();
      setRecommendations(data.recommendations || []);
    } catch (error) {
      console.error("推薦API呼び出しエラー:", error);
      setRecommendationError(
        error instanceof Error ? error.message : "推薦の取得に失敗しました"
      );
    } finally {
      setRecommendationLoading(false);
    }
  };

  const handleReset = () => {
    setQuery("");
    setCompany("");
    setResults([]);
    setRecommendations([]);
    setRecommendationError(null);
    setVendorForm({
      priorities: [],
      developmentStyle: "",
      companySize: "",
      techStack: [],
      industry: "",
      ipOwnership: "",
      partnership: "",
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
            AI ベンダーの選定を質問形式でサポートします
          </p>
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          <form onSubmit={handleGuidedSearch} className="space-y-5" style={{ gap: "20px" }}>
            {/* Q1: プロジェクトの性質（複数選択可） */}
            <div className="bg-gray-50 border border-gray-200 rounded-xl p-5">
              <label className="flex items-center gap-2 text-base font-semibold text-gray-900 mb-4">
                <span>❓</span>
                <span>1. このプロジェクトで最も重視することは？（複数選択可）</span>
              </label>
              <div className="space-y-3">
                {[
                  { value: "tech_innovation", label: "技術的な先進性・最新技術の活用" },
                  { value: "domain_knowledge", label: "業界知見・ドメイン理解の深さ" },
                  { value: "internalization", label: "内製化支援・ナレッジ移管" },
                  { value: "aws_development", label: "AWS環境での開発・運用" },
                  { value: "cost_performance", label: "コストパフォーマンス" },
                  { value: "implementation_speed", label: "実装スピード" },
                ].map((option) => (
                  <label
                    key={option.value}
                    className="flex items-center gap-3 p-3 bg-white border-2 border-gray-200 rounded-lg cursor-pointer hover:border-blue-500 hover:bg-blue-50 transition-all"
                  >
                    <input
                      type="checkbox"
                      checked={vendorForm.priorities.includes(option.value)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setVendorForm({
                            ...vendorForm,
                            priorities: [...vendorForm.priorities, option.value],
                          });
                        } else {
                          setVendorForm({
                            ...vendorForm,
                            priorities: vendorForm.priorities.filter((v) => v !== option.value),
                          });
                        }
                      }}
                      className="w-5 h-5"
                    />
                    <span className="text-sm text-gray-700">{option.label}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Q2: 開発体制の希望（単一選択） */}
            <div className="bg-gray-50 border border-gray-200 rounded-xl p-5">
              <label className="flex items-center gap-2 text-base font-semibold text-gray-900 mb-4">
                <span>❓</span>
                <span>2. どのような開発体制を希望しますか？</span>
              </label>
              <div className="space-y-3">
                {[
                  { value: "full_outsource", label: "完全受託（丸投げOK）" },
                  { value: "collaborative", label: "協働開発（一緒に作る）" },
                  { value: "internal_support", label: "内製支援・伴走型（最終的に自社で運用）" },
                  { value: "consulting", label: "コンサルティング中心（企画・設計まで）" },
                ].map((option) => (
                  <label
                    key={option.value}
                    className="flex items-center gap-3 p-3 bg-white border-2 border-gray-200 rounded-lg cursor-pointer hover:border-blue-500 hover:bg-blue-50 transition-all"
                  >
                    <input
                      type="radio"
                      name="developmentStyle"
                      value={option.value}
                      checked={vendorForm.developmentStyle === option.value}
                      onChange={(e) =>
                        setVendorForm({ ...vendorForm, developmentStyle: e.target.value })
                      }
                      className="w-5 h-5"
                    />
                    <span className="text-sm text-gray-700">{option.label}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Q3: ベンダーの規模感（単一選択） */}
            <div className="bg-gray-50 border border-gray-200 rounded-xl p-5">
              <label className="flex items-center gap-2 text-base font-semibold text-gray-900 mb-4">
                <span>❓</span>
                <span>3. ベンダーの企業規模について</span>
              </label>
              <div className="space-y-3">
                {[
                  { value: "large", label: "大手・準大手が安心" },
                  { value: "medium", label: "中堅企業（30-100名程度）" },
                  { value: "small", label: "小規模でも専門性が高ければ良い（5-20名程度）" },
                  { value: "no_preference", label: "特にこだわりなし" },
                ].map((option) => (
                  <label
                    key={option.value}
                    className="flex items-center gap-3 p-3 bg-white border-2 border-gray-200 rounded-lg cursor-pointer hover:border-blue-500 hover:bg-blue-50 transition-all"
                  >
                    <input
                      type="radio"
                      name="companySize"
                      value={option.value}
                      checked={vendorForm.companySize === option.value}
                      onChange={(e) =>
                        setVendorForm({ ...vendorForm, companySize: e.target.value })
                      }
                      className="w-5 h-5"
                    />
                    <span className="text-sm text-gray-700">{option.label}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Q4: 技術スタック（複数選択可） */}
            <div className="bg-gray-50 border border-gray-200 rounded-xl p-5">
              <label className="flex items-center gap-2 text-base font-semibold text-gray-900 mb-4">
                <span>❓</span>
                <span>4. 必須の技術要件はありますか？（複数選択可）</span>
              </label>
              <div className="space-y-3">
                {[
                  { value: "aws", label: "AWS（必須）" },
                  { value: "azure_gcp", label: "Azure/GCP" },
                  { value: "ai_ml", label: "AI/機械学習" },
                  { value: "modern_web", label: "モダンWeb技術（React/Vue等）" },
                  { value: "data_analysis", label: "データ分析基盤" },
                  { value: "none", label: "特になし" },
                ].map((option) => (
                  <label
                    key={option.value}
                    className="flex items-center gap-3 p-3 bg-white border-2 border-gray-200 rounded-lg cursor-pointer hover:border-blue-500 hover:bg-blue-50 transition-all"
                  >
                    <input
                      type="checkbox"
                      checked={vendorForm.techStack.includes(option.value)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setVendorForm({
                            ...vendorForm,
                            techStack: [...vendorForm.techStack, option.value],
                          });
                        } else {
                          setVendorForm({
                            ...vendorForm,
                            techStack: vendorForm.techStack.filter((v) => v !== option.value),
                          });
                        }
                      }}
                      className="w-5 h-5"
                    />
                    <span className="text-sm text-gray-700">{option.label}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Q5: 対象業界・ドメイン（単一選択） */}
            <div className="bg-gray-50 border border-gray-200 rounded-xl p-5">
              <label className="flex items-center gap-2 text-base font-semibold text-gray-900 mb-4">
                <span>❓</span>
                <span>5. プロジェクトの対象業界は？</span>
              </label>
              <div className="space-y-3">
                {[
                  { value: "manufacturing", label: "製造業・工場" },
                  { value: "logistics", label: "物流・サプライチェーン" },
                  { value: "trading", label: "商社・貿易" },
                  { value: "finance", label: "金融・保険" },
                  { value: "generic", label: "汎用的なシステム" },
                ].map((option) => (
                  <label
                    key={option.value}
                    className="flex items-center gap-3 p-3 bg-white border-2 border-gray-200 rounded-lg cursor-pointer hover:border-blue-500 hover:bg-blue-50 transition-all"
                  >
                    <input
                      type="radio"
                      name="industry"
                      value={option.value}
                      checked={vendorForm.industry === option.value}
                      onChange={(e) =>
                        setVendorForm({ ...vendorForm, industry: e.target.value })
                      }
                      className="w-5 h-5"
                    />
                    <span className="text-sm text-gray-700">{option.label}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Q6: 知財・所有権（単一選択） */}
            <div className="bg-gray-50 border border-gray-200 rounded-xl p-5">
              <label className="flex items-center gap-2 text-base font-semibold text-gray-900 mb-4">
                <span>❓</span>
                <span>6. 開発したシステムの所有権について</span>
              </label>
              <div className="space-y-3">
                {[
                  { value: "full_transfer", label: "当社に完全譲渡してほしい" },
                  { value: "standard", label: "標準的な契約で問題ない" },
                  { value: "vendor_keep", label: "ベンダー側保持でも構わない" },
                  { value: "undecided", label: "まだ決めていない" },
                ].map((option) => (
                  <label
                    key={option.value}
                    className="flex items-center gap-3 p-3 bg-white border-2 border-gray-200 rounded-lg cursor-pointer hover:border-blue-500 hover:bg-blue-50 transition-all"
                  >
                    <input
                      type="radio"
                      name="ipOwnership"
                      value={option.value}
                      checked={vendorForm.ipOwnership === option.value}
                      onChange={(e) =>
                        setVendorForm({ ...vendorForm, ipOwnership: e.target.value })
                      }
                      className="w-5 h-5"
                    />
                    <span className="text-sm text-gray-700">{option.label}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Q7: パートナーシップの志向（単一選択） */}
            <div className="bg-gray-50 border border-gray-200 rounded-xl p-5">
              <label className="flex items-center gap-2 text-base font-semibold text-gray-900 mb-4">
                <span>❓</span>
                <span>7. このプロジェクト後の関係性は？</span>
              </label>
              <div className="space-y-3">
                {[
                  { value: "one_time", label: "単発で完結させたい" },
                  { value: "ongoing", label: "良ければ継続的に依頼したい" },
                  { value: "strategic", label: "長期的な戦略パートナーを探している" },
                ].map((option) => (
                  <label
                    key={option.value}
                    className="flex items-center gap-3 p-3 bg-white border-2 border-gray-200 rounded-lg cursor-pointer hover:border-blue-500 hover:bg-blue-50 transition-all"
                  >
                    <input
                      type="radio"
                      name="partnership"
                      value={option.value}
                      checked={vendorForm.partnership === option.value}
                      onChange={(e) =>
                        setVendorForm({ ...vendorForm, partnership: e.target.value })
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
                disabled={recommendationLoading}
                className="w-full px-4 py-4 bg-gradient-to-r from-blue-600 to-blue-700 text-white rounded-xl font-semibold hover:from-blue-700 hover:to-blue-800 transition-all shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
              >
                {recommendationLoading ? (
                  <>
                    <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    <span>検索中...</span>
                  </>
                ) : (
                  <>
                    <span>🔍</span>
                    <span>おすすめベンダーを検索</span>
                  </>
                )}
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

          {/* 推薦結果表示エリア */}
          {recommendationError && (
            <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-800 font-medium">エラー</p>
              <p className="text-sm text-red-600 mt-1">{recommendationError}</p>
            </div>
          )}

          {recommendations.length > 0 && (
            <div className="mt-6 space-y-4">
              <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                <span>⭐</span>
                <span>推薦ベンダー TOP{recommendations.length}</span>
              </h3>
              {recommendations.map((rec, index) => (
                <div
                  key={index}
                  className="bg-white border-2 border-gray-200 rounded-xl p-5 hover:border-blue-500 hover:shadow-md transition-all"
                >
                  <div className="flex justify-between items-start mb-3">
                    <h4 className="text-lg font-bold text-gray-900">
                      {rec.company_name}
                    </h4>
                    <span className="bg-green-100 text-green-800 px-3 py-1 rounded-full text-sm font-semibold">
                      マッチ度: {rec.match_score}%
                    </span>
                  </div>
                  
                  {/* スコアプログレスバー */}
                  <div className="mb-4">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs text-gray-600 font-medium">適合度</span>
                      <span className="text-xs text-gray-500">{rec.match_score}%</span>
                    </div>
                    <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-blue-500 to-blue-600 rounded-full transition-all duration-500"
                        style={{ width: `${rec.match_score}%` }}
                      />
                    </div>
                  </div>

                  {/* 推薦理由 */}
                  <div className="mt-4">
                    <p className="text-sm text-gray-700 leading-relaxed">
                      {rec.reasoning}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ユーティリティ関数
function hasSelection(form: VendorSearchForm): boolean {
  return (
    form.priorities.length > 0 ||
    form.developmentStyle !== "" ||
    form.companySize !== "" ||
    form.techStack.length > 0 ||
    form.industry !== "" ||
    form.ipOwnership !== "" ||
    form.partnership !== ""
  );
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
  form: VendorSearchForm
): SearchResult[] {
  const companies = ["LaboroAI", "BrainPad", "NUCO", "LiberCraft", "Akari"];
  return companies.map((comp, index) => ({
    id: `guided-${index}`,
    text: `${comp}は、あなたの要件に合致したベンダーです。${form.priorities.length > 0 ? `重視項目: ${form.priorities.join(", ")}` : ""}`,
    title: `${comp} - 推薦ベンダー`,
    snippet: `${comp}は、あなたの要件に合致したベンダーです。`,
    meta: {
      vendor_name: comp,
      meeting_date: new Date().toISOString().split("T")[0],
      doc_type: "推薦",
    },
  }));
}
