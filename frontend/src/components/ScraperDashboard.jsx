import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  BarChart3, 
  Activity, 
  AlertCircle, 
  RefreshCcw, 
  CheckCircle2, 
  Clock, 
  Database,
  History,
  Plus,
  Globe,
  ExternalLink,
  Trash2,
  Settings2,
  Sparkles,
  Package
} from "lucide-react";
import { getScraperStats, getScraperJobs, getDeadLetters, clearQuotaError, getSites, addSite, updateSite, startCrawl, deleteSite, resetSite, resetAllData, runCategorization } from "../api/admin";
import CrawlerConsole from "./admin/CrawlerConsole";
import ProductsTab from "./admin/ProductsTab";

export default function ScraperDashboard() {
  const [stats, setStats] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [sites, setSites] = useState([]);
  const [deadLetters, setDeadLetters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [activeTab, setActiveTab] = useState("overview"); // "overview" | "products" | "history" | "failures"
  
  const [showAddForm, setShowAddForm] = useState(false);
  const [newSite, setNewSite] = useState({ domain: "", root_url: "" });
  
  const [activeIndexingSite, setActiveIndexingSite] = useState(null);

  const fetchData = useCallback(async (showRefresh = false) => {
    if (showRefresh) setRefreshing(true);
    try {
      const [s, j, d, st] = await Promise.all([
        getScraperStats(),
        getScraperJobs(10),
        getDeadLetters(20),
        getSites()
      ]);
      setStats(s);
      setJobs(j.jobs);
      setDeadLetters(d);
      setSites(st);
    } catch (error) {
      console.error("Failed to fetch dashboard data:", error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    const initial = setTimeout(() => fetchData(), 0);
    const interval = setInterval(() => fetchData(), 30000);
    return () => { clearTimeout(initial); clearInterval(interval); };
  }, [fetchData]);

  const handleAddSite = async (e) => {
    e.preventDefault();
    try {
      await addSite(newSite);
      setNewSite({ domain: "", root_url: "" });
      setShowAddForm(false);
      fetchData(true);
    } catch (error) {
      alert(`Failed to add site: ${error.message}`);
    }
  };

  const handleEditSite = async (siteId, siteData) => {
    try {
      await updateSite(siteId, siteData);
      fetchData(true);
    } catch (error) {
      alert(`Failed to update site: ${error.message}`);
    }
  };

  const handleStartIndexing = async (site) => {
    try {
      await startCrawl(site.id);
      setActiveIndexingSite(site);
    } catch (error) {
      alert(`Failed to start indexing: ${error.message}`);
    }
  };

  const handleDeleteSite = async (siteId) => {
    if (!confirm("Are you sure you want to delete this site and all its indexed products?")) return;
    try {
      await deleteSite(siteId);
      fetchData(true);
    } catch (error) {
      alert(`Failed to delete site: ${error.message}`);
    }
  };

  const handleResetSite = async (siteId) => {
    if (!confirm("This will wipe all indexed products and 'memory' for this site. The AI will also re-analyze the site structure on next run. Proceed?")) return;
    try {
      await resetSite(siteId);
      fetchData(true);
    } catch (error) {
      alert(`Failed to reset site: ${error.message}`);
    }
  };

  const handleReset = async () => {
    if (!confirm("CRITICAL ACTION: This will wipe ALL sites, products, and crawl history. Proceed?")) return;
    try {
      await resetAllData();
      fetchData(true);
    } catch (error) {
      alert(`Failed to reset data: ${error.message}`);
    }
  };

  const handleAIByBatch = async () => {
    try {
      setRefreshing(true);
      await runCategorization(300);
      alert("AI Categorization job started in the background. Results will appear as they are processed.");
    } catch (error) {
      alert(`Failed to start AI job: ${error.message}`);
    } finally {
      setRefreshing(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-32 animate-pulse bg-light">
        <Activity className="w-12 h-12 text-accent mb-4 animate-spin" strokeWidth={1.5} />
        <p className="text-muted font-serif italic text-lg">Initializing fashion engine...</p>
      </div>
    );
  }

  return (
    <div className="flex-1 bg-light px-5 md:px-12 py-10 space-y-12">
      {/* ── Header & Navigation ─────────────────────────────────── */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 border-b border-bordercolor pb-8">
        <div>
          <h1 className="text-4xl md:text-5xl font-serif font-semibold text-navy tracking-tight mb-2">
            Scraper <span className="text-accent italic font-light">Analytics</span>
          </h1>
          <p className="text-muted font-sans text-sm tracking-wide uppercase">Monitor and manage the ingestion pipeline</p>
        </div>

        <div className="flex items-center gap-1 bg-white border border-bordercolor p-1 rounded-full shadow-sm">
          {[
            { id: "overview", label: "Overview", icon: BarChart3 },
            { id: "products", label: "Products", icon: Package },
            { id: "history",  label: "History",  icon: History },
            { id: "failures", label: "Failures", icon: AlertCircle },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-6 py-2.5 rounded-full text-xs font-bold transition-all ${
                activeTab === tab.id 
                  ? "bg-navy text-white shadow-md" 
                  : "text-muted hover:text-navy hover:bg-light"
              }`}
            >
              <tab.icon className="w-3.5 h-3.5" />
              {tab.label}
            </button>
          ))}
          <div className="w-px h-4 bg-bordercolor mx-2" />
          <button 
            onClick={() => fetchData(true)}
            disabled={refreshing}
            className="p-2.5 text-muted hover:text-accent transition-colors disabled:opacity-50"
          >
            <RefreshCcw className={`w-4 h-4 ${refreshing ? "animate-spin" : ""}`} />
          </button>
          <div className="w-px h-4 bg-bordercolor mx-2" />
          <button 
            onClick={handleReset}
            className="p-2.5 text-red-400 hover:text-red-600 transition-colors"
            title="Reset All Data"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      <AnimatePresence mode="wait">
        {activeTab === "overview" && (
          <motion.div 
            key="overview"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="space-y-12"
          >
            {/* Stats Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
              <StatCard 
                label="Total Products" 
                value={stats?.total_products || 0} 
                icon={Database}
                sub={`${stats?.active_products || 0} Active`}
              />
              <StatCard 
                label="Success Rate" 
                value={`${stats?.success_rate || 0}%`} 
                icon={CheckCircle2}
                sub="Last 50 jobs"
              />
              <StatCard 
                label="Dead Letters" 
                value={stats?.failed_products_count || 0} 
                icon={AlertCircle}
                sub="Requires review"
                isAlert={stats?.failed_products_count > 0}
              />
              <StatCard 
                label="Total Jobs" 
                value={stats?.total_jobs || 0} 
                icon={Clock}
                sub="Lifetime runs"
              />
            </div>

            {/* Site Management Section */}
            <section>
              <div className="flex items-center justify-between mb-8">
                <h2 className="text-2xl font-serif font-semibold text-navy flex items-center gap-3">
                  <Activity className="w-6 h-6 text-accent" />
                  Target Sites
                </h2>
                <div className="flex gap-3">
                  <button 
                    onClick={handleAIByBatch}
                    className="flex items-center gap-2 px-5 py-2.5 rounded-full border border-accent text-accent hover:bg-accent hover:text-white transition-all text-xs font-bold shadow-lg shadow-accent/5"
                  >
                    <Sparkles className="w-4 h-4" />
                    AI Categorize (Batch)
                  </button>
                  <button 
                    onClick={() => setShowAddForm(!showAddForm)}
                    className="flex items-center gap-2 px-5 py-2.5 rounded-full bg-accent text-white hover:bg-navy transition-all text-xs font-bold shadow-lg shadow-accent/20"
                  >
                    <Plus className="w-4 h-4" />
                    Register New Site
                  </button>
                </div>
              </div>

              <AnimatePresence>
                {showAddForm && (
                  <motion.form 
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    onSubmit={handleAddSite}
                    className="mb-10 p-8 rounded-3xl bg-white border border-accent/20 shadow-xl shadow-accent/5 overflow-hidden"
                  >
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                      <div>
                        <label className="block text-[11px] uppercase tracking-widest text-muted mb-2 font-bold">Domain (e.g. vogue.com)</label>
                        <input 
                          required
                          type="text" 
                          placeholder="nike.com"
                          className="w-full bg-light border border-bordercolor rounded-2xl px-5 py-3.5 text-sm focus:border-accent outline-none transition-all font-sans"
                          value={newSite.domain}
                          onChange={e => setNewSite({...newSite, domain: e.target.value.toLowerCase()})}
                        />
                      </div>
                      <div>
                        <label className="block text-[11px] uppercase tracking-widest text-muted mb-2 font-bold">Root URL (Homepage)</label>
                        <input 
                          required
                          type="url" 
                          placeholder="https://..."
                          className="w-full bg-light border border-bordercolor rounded-2xl px-5 py-3.5 text-sm focus:border-accent outline-none transition-all font-sans"
                          value={newSite.root_url}
                          onChange={e => setNewSite({...newSite, root_url: e.target.value})}
                        />
                      </div>
                    </div>
                    <div className="flex justify-end gap-4">
                      <button 
                        type="button"
                        onClick={() => setShowAddForm(false)}
                        className="px-6 py-3 text-xs font-bold text-muted hover:text-navy transition-colors"
                      >
                        Cancel
                      </button>
                      <button 
                        type="submit"
                        className="px-8 py-3 bg-navy text-white rounded-full text-xs font-bold shadow-xl hover:bg-accent transition-all"
                      >
                        Add to Ingestion Engine
                      </button>
                    </div>
                  </motion.form>
                )}
              </AnimatePresence>

              <div className="grid grid-cols-1 gap-6">
                {sites.map((site) => (
                  <SiteCard 
                    key={site.id} 
                    site={site} 
                    onTrigger={handleStartIndexing}
                    onDelete={() => handleDeleteSite(site.id)}
                    onReset={() => handleResetSite(site.id)}
                    onEdit={(data) => handleEditSite(site.id, data)}
                  />
                ))}
              </div>
            </section>

            {/* Recent Activity Section */}
            <section className="bg-white rounded-[40px] p-8 border border-bordercolor shadow-sm">
              <div className="flex items-center justify-between mb-8">
                <h2 className="text-2xl font-serif font-semibold text-navy flex items-center gap-3">
                  <History className="w-6 h-6 text-accent" />
                  Recent Pipeline Activity
                </h2>
                <button onClick={() => setActiveTab("history")} className="text-xs font-bold text-accent hover:underline uppercase tracking-widest">Explore all jobs</button>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left">
                  <thead>
                    <tr className="text-muted text-[10px] uppercase tracking-[0.2em] border-b border-bordercolor">
                      <th className="pb-4 pl-2 font-black">Site</th>
                      <th className="pb-4 font-black">Started</th>
                      <th className="pb-4 font-black">Status</th>
                      <th className="pb-4 text-right pr-2 font-black">Scraped</th>
                    </tr>
                  </thead>
                  <tbody className="text-sm">
                    {jobs.slice(0, 5).map((job) => (
                      <tr key={job.id} className="border-b border-bordercolor/50 hover:bg-light/30 transition-colors group">
                        <td className="py-5 pl-2 font-bold text-navy">{job.site}</td>
                        <td className="py-5 text-muted text-xs">
                          {new Date(job.started_at).toLocaleString([], { hour: '2-digit', minute: '2-digit', month: 'short', day: 'numeric' })}
                        </td>
                        <td className="py-5">
                          <StatusBadge status={job.status} />
                        </td>
                        <td className="py-5 text-right pr-2 font-sans font-medium text-navy">{job.products_scraped}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </motion.div>
        )}

        {activeTab === "history" && (
          <motion.div 
            key="history"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            className="bg-white rounded-[40px] p-10 border border-bordercolor shadow-sm"
          >
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead>
                  <tr className="text-muted text-[10px] uppercase tracking-[0.2em] border-b border-bordercolor">
                    <th className="pb-6 pl-2 font-black">Job ID</th>
                    <th className="pb-6 font-black">Site</th>
                    <th className="pb-6 font-black">Started</th>
                    <th className="pb-6 font-black">Duration</th>
                    <th className="pb-6 font-black">Status</th>
                    <th className="pb-6 text-right pr-2 font-black">Products</th>
                  </tr>
                </thead>
                <tbody className="text-sm">
                  {jobs.map((job) => {
                    const duration = job.finished_at 
                      ? Math.round((new Date(job.finished_at) - new Date(job.started_at)) / 1000)
                      : null;
                    return (
                      <tr key={job.id} className="border-b border-bordercolor/50 hover:bg-light/30 transition-colors">
                        <td className="py-5 pl-2 text-muted font-sans text-[10px]">#{job.id}</td>
                        <td className="py-5 font-bold text-navy">{job.site}</td>
                        <td className="py-5 text-muted text-xs">
                          {new Date(job.started_at).toLocaleString()}
                        </td>
                        <td className="py-5 text-muted text-xs font-medium">
                          {duration ? `${duration}s` : job.status === 'running' ? '—' : 'n/a'}
                        </td>
                        <td className="py-5">
                          <StatusBadge status={job.status} />
                          {job.error_message && (
                            <p className="text-[10px] text-red-500 mt-2 max-w-[240px] leading-relaxed italic" title={job.error_message}>
                              {job.error_message}
                            </p>
                          )}
                        </td>
                        <td className="py-5 text-right pr-2 font-bold text-navy">{job.products_scraped}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </motion.div>
        )}

        {activeTab === "failures" && (
          <motion.div 
            key="failures"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            className="grid grid-cols-1 md:grid-cols-2 gap-6"
          >
            {deadLetters.length === 0 ? (
              <div className="col-span-full bg-white rounded-[40px] p-24 text-center border border-bordercolor shadow-sm">
                <CheckCircle2 className="w-16 h-16 text-green-500/30 mx-auto mb-6" />
                <h3 className="text-2xl font-serif font-semibold text-navy mb-2">Immaculate Pipeline</h3>
                <p className="text-muted">No ingestion failures detected. Your data stream is perfectly curated.</p>
              </div>
            ) : (
              deadLetters.map((entry, i) => (
                <div key={i} className="bg-white rounded-3xl p-6 flex flex-col gap-4 items-start border border-bordercolor hover:border-red-200 transition-all shadow-sm group">
                  <div className="w-full flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-[10px] font-black uppercase tracking-widest px-2.5 py-1 rounded-full bg-red-50 text-red-600 border border-red-100">
                        {entry.source_site}
                      </span>
                      <span className="text-[10px] text-muted font-sans tracking-wide">
                        {new Date(entry.timestamp).toLocaleString()}
                      </span>
                    </div>
                    <p className="text-sm text-navy font-bold mb-2 truncate group-hover:text-red-600 transition-colors" title={entry.product_url}>
                      {entry.product_url}
                    </p>
                    <div className="p-4 rounded-2xl bg-red-50/30 border border-red-50 text-[12px] text-red-600/80 leading-relaxed font-sans">
                      <span className="font-black uppercase text-[9px] block mb-1">Issue Detected</span>
                      {entry.reason}
                    </div>
                  </div>
                  <a 
                    href={entry.product_url} 
                    target="_blank" 
                    rel="noreferrer"
                    className="w-full text-center py-3 rounded-full bg-light hover:bg-navy hover:text-white text-xs font-black transition-all uppercase tracking-widest"
                  >
                    Resolve in browser
                  </a>
                </div>
              ))
            )}
          </motion.div>
        )}
        {activeTab === "products" && (
          <motion.div 
            key="products"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
          >
            <ProductsTab />
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {activeIndexingSite && (
          <CrawlerConsole 
            site={activeIndexingSite} 
            onClose={() => setActiveIndexingSite(null)} 
          />
        )}
      </AnimatePresence>

      <QuotaModal 
        status={stats?.quota_status} 
        onClear={async () => {
          await clearQuotaError();
          fetchData(true);
        }} 
      />
    </div>
  );
}

function QuotaModal({ status, onClear }) {
  if (!status || !status.is_blocked) return null;

  return (
    <motion.div 
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="fixed inset-0 z-[100] flex items-center justify-center p-6 bg-navy/60 backdrop-blur-md"
    >
      <motion.div 
        initial={{ scale: 0.9, y: 20 }}
        animate={{ scale: 1, y: 0 }}
        className="bg-white rounded-[40px] shadow-2xl max-w-lg w-full overflow-hidden border border-red-100"
      >
        <div className="bg-red-50 p-10 flex flex-col items-center text-center">
          <div className="w-20 h-20 rounded-full bg-red-100 flex items-center justify-center text-red-600 mb-6 shadow-inner">
            <AlertCircle className="w-10 h-10" />
          </div>
          <h2 className="text-3xl font-serif font-bold text-navy mb-4">API Quota Exhausted</h2>
          <p className="text-red-600/80 text-sm leading-relaxed font-sans font-medium px-4">
            {status.error || "You've exceeded your Gemini API free tier limit (20 requests/day)."}
          </p>
        </div>
        
        <div className="p-10 space-y-8">
          <div className="space-y-2">
            <div className="flex justify-between text-[10px] font-black uppercase tracking-widest text-muted">
              <span>Cooling Down</span>
              <span className="text-accent">Available at: {new Date(status.retry_after).toLocaleTimeString()}</span>
            </div>
            <div className="h-1.5 w-full bg-light rounded-full overflow-hidden">
              <motion.div 
                initial={{ width: "100%" }}
                animate={{ width: "0%" }}
                transition={{ duration: 60, ease: "linear" }}
                className="h-full bg-accent"
              />
            </div>
          </div>

          <div className="flex flex-col gap-3">
            <button 
              onClick={onClear}
              className="w-full py-4 rounded-full bg-navy text-white text-xs font-black uppercase tracking-widest hover:bg-accent transition-all shadow-xl shadow-navy/20"
            >
              Acknowledge & Clear
            </button>
            <p className="text-[10px] text-center text-muted italic">
              Clearing manually won't bypass Google's limit, but it resets the UI.
            </p>
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
}

function SiteCard({ site, onTrigger, onDelete, onReset, onEdit }) {
  const [isEditing, setIsEditing] = useState(false);
  const [editData, setEditData] = useState({ domain: site.domain, root_url: site.root_url });

  return (
    <div className="bg-white border border-bordercolor rounded-3xl p-8 hover:shadow-2xl hover:shadow-navy/5 transition-all group relative overflow-hidden">
      {isEditing ? (
        <div className="space-y-4">
          <div>
            <label className="block text-[10px] uppercase font-bold text-muted mb-1">Domain</label>
            <input 
              className="w-full bg-light border border-bordercolor rounded-xl px-4 py-2 text-sm outline-none focus:border-accent"
              value={editData.domain}
              onChange={e => setEditData({...editData, domain: e.target.value})}
            />
          </div>
          <div>
            <label className="block text-[10px] uppercase font-bold text-muted mb-1">Root URL</label>
            <input 
              className="w-full bg-light border border-bordercolor rounded-xl px-4 py-2 text-sm outline-none focus:border-accent"
              value={editData.root_url}
              onChange={e => setEditData({...editData, root_url: e.target.value})}
            />
          </div>
          <div className="flex gap-2 pt-2">
            <button 
              onClick={() => {
                onEdit(editData);
                setIsEditing(false);
              }}
              className="flex-1 bg-navy text-white text-xs font-bold py-2 rounded-xl hover:bg-accent transition-colors"
            >
              Save
            </button>
            <button 
              onClick={() => setIsEditing(false)}
              className="flex-1 bg-light text-muted text-xs font-bold py-2 rounded-xl hover:bg-bordercolor transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <>
          <div className="flex items-start justify-between mb-6">
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 rounded-2xl bg-light flex items-center justify-center text-navy group-hover:bg-navy group-hover:text-white transition-all duration-500 shadow-inner">
                <Globe className="w-6 h-6" />
              </div>
              <div>
                <h3 className="font-bold text-navy text-lg leading-tight">{site.domain}</h3>
                <p className="text-xs text-muted font-medium mt-1">
                  {site.total_products || 0} products indexed
                </p>
              </div>
            </div>
            <div className={`px-4 py-1.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
              site.status === "crawling" ? "bg-green-50 text-green-600 border border-green-100 animate-pulse" : "bg-light text-muted border border-bordercolor"
            }`}>
              {site.status || "idle"}
            </div>
          </div>

          <div className="flex items-center gap-3">
            <a 
              href={site.root_url} 
              target="_blank" 
              rel="noreferrer"
              className="w-12 h-12 rounded-full border border-bordercolor flex items-center justify-center text-muted hover:text-navy hover:bg-white hover:shadow-md transition-all group/link"
              title="Visit Site"
            >
              <ExternalLink className="w-4 h-4 transition-transform group-hover/link:-translate-y-0.5 group-hover/link:translate-x-0.5" />
            </a>
            <button 
              onClick={() => setIsEditing(true)}
              className="w-12 h-12 rounded-full border border-bordercolor flex items-center justify-center text-muted hover:text-navy hover:bg-white hover:shadow-md transition-all"
              title="Edit Site"
            >
              <Settings2 className="w-4 h-4" />
            </button>
            <button 
              onClick={onDelete}
              className="w-12 h-12 rounded-full border border-red-100 flex items-center justify-center text-red-300 hover:text-red-500 hover:bg-red-50 transition-all"
              title="Delete Site"
            >
              <Trash2 className="w-4 h-4" />
            </button>
            <button 
              onClick={onReset}
              className="w-12 h-12 rounded-full border border-orange-100 flex items-center justify-center text-orange-300 hover:text-orange-500 hover:bg-orange-50 transition-all"
              title="Reset Site Data (Wipe products & memory)"
            >
              <RefreshCcw className="w-4 h-4" />
            </button>
            <button 
              onClick={() => onTrigger(site)}
              className="flex items-center gap-3 pl-6 pr-4 py-3 rounded-full bg-navy text-white hover:bg-accent transition-all shadow-xl shadow-navy/10 group/btn"
            >
              <span className="text-xs font-bold uppercase tracking-widest">Index Now</span>
              <div className="w-8 h-8 rounded-full bg-white/10 flex items-center justify-center group-hover/btn:rotate-45 transition-transform duration-500">
                <Plus className="w-4 h-4" />
              </div>
            </button>
          </div>
        </>
      )}
    </div>
  );
}

function StatCard({ label, value, icon: Icon, sub, isAlert }) {
  return (
    <div className={`bg-white rounded-3xl p-7 border transition-all hover:shadow-xl hover:shadow-navy/5 group ${isAlert ? 'border-red-100 ring-2 ring-red-50 ring-opacity-50' : 'border-bordercolor'}`}>
      <div className="flex items-center justify-between mb-6">
        <div className={`p-3.5 rounded-2xl transition-all ${isAlert ? 'bg-red-50 text-red-600' : 'bg-light text-muted group-hover:bg-accent group-hover:text-white group-hover:scale-110 shadow-sm'}`}>
          <Icon className="w-6 h-6" strokeWidth={1.5} />
        </div>
      </div>
      <div>
        <p className={`text-4xl font-serif font-semibold mb-1 ${isAlert ? 'text-red-600' : 'text-navy'}`}>{value}</p>
        <p className="text-[11px] font-black text-muted uppercase tracking-[0.15em]">{label}</p>
        {sub && <p className="text-[11px] text-muted mt-3 font-sans opacity-70 italic">{sub}</p>}
      </div>
    </div>
  );
}

function StatusBadge({ status }) {
  const styles = {
    running: "bg-blue-50 text-blue-600 border-blue-100",
    completed: "bg-green-50 text-green-600 border-green-100",
    failed: "bg-red-50 text-red-600 border-red-100",
  };

  return (
    <span className={`px-4 py-1.5 rounded-full text-[10px] font-black uppercase tracking-widest border shadow-sm ${styles[status] || styles.failed}`}>
      {status}
    </span>
  );
}
