import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  BarChart3, 
  Activity, 
  AlertCircle, 
  RefreshCcw, 
  CheckCircle2, 
  XCircle, 
  Clock, 
  Database,
  Play,
  History,
  LayoutDashboard,
  Plus,
  Globe,
  ExternalLink,
  Trash2
} from "lucide-react";
import { getScraperStats, getScraperJobs, getDeadLetters, triggerScrape, getSites, addSite, startCrawl, deleteSite, resetAllData } from "../api/admin";
import CrawlerConsole from "./admin/CrawlerConsole";

export default function ScraperDashboard() {
  const [stats, setStats] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [sites, setSites] = useState([]);
  const [deadLetters, setDeadLetters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [activeTab, setActiveTab] = useState("overview"); // "overview" | "history" | "failures"
  
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
    fetchData();
    const interval = setInterval(() => fetchData(), 30000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const handleTrigger = async (site, category = null, gender = null) => {
    try {
      await triggerScrape(site, category, gender);
      fetchData(true);
    } catch (error) {
      alert(`Failed to trigger: ${error.message}`);
    }
  };

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

  const handleReset = async () => {
    if (!confirm("CRITICAL ACTION: This will wipe ALL sites, products, and crawl history. Proceed?")) return;
    try {
      await resetAllData();
      fetchData(true);
    } catch (error) {
      alert(`Failed to reset data: ${error.message}`);
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
                <button 
                  onClick={() => setShowAddForm(!showAddForm)}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-full bg-accent text-white hover:bg-navy transition-all text-xs font-bold shadow-lg shadow-accent/20"
                >
                  <Plus className="w-4 h-4" />
                  Register New Site
                </button>
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
                    key={site.domain} 
                    site={site} 
                    lastJob={jobs.find(j => j.site === site.domain)} 
                    onTrigger={handleStartIndexing}
                    onDelete={() => handleDeleteSite(site.id)}
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
      </AnimatePresence>

      <AnimatePresence>
        {activeIndexingSite && (
          <CrawlerConsole 
            site={activeIndexingSite} 
            onClose={() => setActiveIndexingSite(null)} 
          />
        )}
      </AnimatePresence>
    </div>
  );
}

function SiteCard({ site, lastJob, onTrigger, onDelete }) {
  const [category, setCategory] = useState("");
  const [gender, setGender] = useState("");

  return (
    <div className="bg-white p-6 md:p-8 rounded-[32px] border border-bordercolor shadow-sm hover:shadow-xl hover:shadow-navy/5 transition-all group flex flex-col md:flex-row md:items-center justify-between gap-8">
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-4">
          <div className="p-3 rounded-2xl bg-light text-muted group-hover:text-accent group-hover:bg-accent/5 transition-all shadow-sm">
            <Globe className="w-5 h-5" />
          </div>
          <div>
            <p className="font-serif text-xl font-semibold text-navy truncate">{site.domain}</p>
            <p className="text-[10px] text-muted mt-1 uppercase tracking-widest font-sans font-bold flex items-center gap-2">
              <Clock className="w-3 h-3" />
              {lastJob ? `Last Active: ${new Date(lastJob.started_at).toLocaleString()}` : 'Never processed'}
            </p>
          </div>
        </div>
      </div>

      <div className="flex flex-col sm:flex-row items-center gap-4 bg-light/50 p-2 rounded-[24px] border border-bordercolor/50">
        <div className="flex flex-col gap-1 px-3">
          <label className="text-[9px] uppercase tracking-tighter text-muted font-black">Tag Category</label>
          <input 
            type="text" 
            placeholder="e.g. Shoes"
            className="bg-transparent border-none outline-none text-xs text-navy font-bold placeholder:text-muted/50 w-24"
            value={category}
            onChange={e => setCategory(e.target.value)}
          />
        </div>
        <div className="w-px h-8 bg-bordercolor/50 hidden sm:block" />
        <div className="flex flex-col gap-1 px-3">
          <label className="text-[9px] uppercase tracking-tighter text-muted font-black">Tag Gender</label>
          <select 
            className="bg-transparent border-none outline-none text-xs text-navy font-bold cursor-pointer"
            value={gender}
            onChange={e => setGender(e.target.value)}
          >
            <option value="">Unisex/Auto</option>
            <option value="women">Women</option>
            <option value="men">Men</option>
          </select>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <a 
          href={site.root_url} 
          target="_blank" 
          rel="noreferrer"
          className="w-12 h-12 rounded-full border border-bordercolor flex items-center justify-center text-muted hover:text-navy hover:bg-white hover:shadow-md transition-all group/link"
          title="Open listing URL"
        >
          <ExternalLink className="w-4 h-4 transition-transform group-hover/link:-translate-y-0.5 group-hover/link:translate-x-0.5" />
        </a>
        <button 
          onClick={onDelete}
          className="w-12 h-12 rounded-full border border-red-100 flex items-center justify-center text-red-300 hover:text-red-500 hover:bg-red-50 transition-all"
          title="Delete Site"
        >
          <Trash2 className="w-4 h-4" />
        </button>
        <button 
          onClick={() => onTrigger(site)}
          className="flex items-center gap-3 pl-6 pr-4 py-3 rounded-full bg-navy text-white hover:bg-accent transition-all shadow-xl shadow-navy/10 group/btn"
        >
          <span className="text-xs font-black uppercase tracking-widest">Start Indexing</span>
          <div className="w-8 h-8 rounded-full bg-white/10 flex items-center justify-center transition-transform group-hover/btn:scale-110">
            <Play className="w-3 h-3 fill-current ml-0.5" />
          </div>
        </button>
      </div>
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
