import { useState, useCallback } from "react";
import { LayoutDashboard, Search } from "lucide-react";
import ImageUpload from "./components/ImageUpload";
import SearchBar from "./components/SearchBar";
import ProductGrid from "./components/ProductGrid";
import SkeletonLoader from "./components/SkeletonLoader";
import ScraperDashboard from "./components/ScraperDashboard";
import { searchByImage, searchByText } from "./api/search";

// State machine: "home" | "loading" | "results" | "error"
export default function App() {
  const [view, setView] = useState("search"); // "search" | "admin"
  const [state, setState] = useState("home");
  const [results, setResults] = useState([]);
  const [queryType, setQueryType] = useState(null);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState("image"); // "image" | "text"

  const handleImageSearch = useCallback(async (file) => {
    setState("loading");
    setQueryType("image");
    setError(null);
    try {
      const data = await searchByImage(file);
      setResults(data.results);
      setState("results");
    } catch (e) {
      setError(e.message);
      setState("error");
    }
  }, []);

  const handleTextSearch = useCallback(async (query) => {
    setState("loading");
    setQueryType("text");
    setError(null);
    try {
      const data = await searchByText(query);
      setResults(data.results);
      setState("results");
    } catch (e) {
      setError(e.message);
      setState("error");
    }
  }, []);

  function reset() {
    setState("home");
    setResults([]);
    setError(null);
    setView("search");
  }

  const isLoading = state === "loading";

  return (
    <div className="min-h-screen flex flex-col">
      {/* ── Header ─────────────────────────────────────── */}
      <header className="sticky top-0 z-20 glass border-b border-white/5 px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <button onClick={reset} className="flex items-center gap-2 group">
            <div className="w-8 h-8 rounded-lg bg-brand-500 flex items-center justify-center
                            shadow-lg shadow-brand-500/40 group-hover:shadow-brand-500/60 transition-shadow">
              <span className="text-white font-bold text-sm">F</span>
            </div>
            <span className="text-lg font-bold tracking-tight">
              Fi<span className="text-brand-400">Fy</span>
            </span>
          </button>

          <div className="flex items-center gap-1 bg-white/5 rounded-xl p-1">
            <button
              onClick={() => setView("search")}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-medium transition-all ${
                view === "search" 
                  ? "bg-white/10 text-white" 
                  : "text-zinc-500 hover:text-zinc-300"
              }`}
            >
              <Search className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Search</span>
            </button>
            <button
              onClick={() => setView("admin")}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-medium transition-all ${
                view === "admin" 
                  ? "bg-white/10 text-white" 
                  : "text-zinc-500 hover:text-zinc-300"
              }`}
            >
              <LayoutDashboard className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Analytics</span>
            </button>
          </div>
        </div>
      </header>

      {/* ── Main ───────────────────────────────────────── */}
      <main className="flex-1 max-w-6xl mx-auto w-full px-4 sm:px-6 py-10">
        {view === "admin" ? (
          <ScraperDashboard />
        ) : (
          <>
            {/* Search Panel — always visible */}
            <section className="glass rounded-3xl p-6 sm:p-8 animate-fade-in">
              {/* Hero text (only on home/error) */}
              {(state === "home" || state === "error") && (
                <div className="mb-8 text-center">
                  <h1 className="text-3xl sm:text-4xl font-bold tracking-tight mb-3">
                    Find fashion by{" "}
                    <span className="text-transparent bg-clip-text bg-gradient-to-r from-brand-400 to-pink-300">
                      photo or description
                    </span>
                  </h1>
                  <p className="text-zinc-400 max-w-xl mx-auto text-sm sm:text-base">
                    Upload a picture or describe what you're looking for — we'll find visually
                    similar items across ASOS, Zara, H&M, Uniqlo, and Zalando.
                  </p>
                </div>
              )}

              {/* Tabs */}
              <div className="flex gap-1 mb-6 bg-white/5 rounded-xl p-1 w-fit">
                {[
                  { key: "image", label: "📷  Photo search" },
                  { key: "text",  label: "✏️  Text search"  },
                ].map(({ key, label }) => (
                  <button
                    key={key}
                    id={`tab-${key}`}
                    onClick={() => setActiveTab(key)}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                      activeTab === key
                        ? "bg-brand-500 text-white shadow-md shadow-brand-500/30"
                        : "text-zinc-400 hover:text-zinc-200"
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>

              {/* Active input */}
              {activeTab === "image" ? (
                <ImageUpload onFile={handleImageSearch} disabled={isLoading} />
              ) : (
                <SearchBar onSearch={handleTextSearch} disabled={isLoading} />
              )}

              {/* Error message */}
              {state === "error" && error && (
                <p className="mt-4 text-sm text-red-400 glass rounded-xl px-4 py-3">
                  ⚠️ {error}
                </p>
              )}
            </section>

            {/* Results area */}
            {state === "loading" && <SkeletonLoader count={8} />}
            {state === "results" && (
              <div className="animate-fade-in">
                <div className="flex items-center justify-between mt-8 mb-2">
                  <span />
                  <button onClick={reset}
                    className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors underline underline-offset-2">
                    New search
                  </button>
                </div>
                <ProductGrid results={results} queryType={queryType} />
              </div>
            )}
          </>
        )}
      </main>

      {/* ── Footer ─────────────────────────────────────── */}
      <footer className="border-t border-white/5 text-center text-xs text-zinc-600 py-6">
        FiFy MVP · CLIP ViT-B/32 · Qdrant · Playwright
      </footer>
    </div>
  );
}
