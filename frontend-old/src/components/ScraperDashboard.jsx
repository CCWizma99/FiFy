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
  ExternalLink
} from "lucide-react";
import { getScraperStats, getScraperJobs, getDeadLetters, triggerScrape, getSites, addSite } from "../api/admin";

export default function ScraperDashboard() {
  const [stats, setStats] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [sites, setSites] = useState([]);
  const [deadLetters, setDeadLetters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [activeTab, setActiveTab] = useState("overview"); // "overview" | "history" | "failures"
  
  // New site form state
  const [showAddForm, setShowAddForm] = useState(false);
  const [newSite, setNewSite] = useState({ domain: "", listing_url: "" });

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
    const interval = setInterval(() => fetchData(), 30000); // Auto refresh every 30s
    return () => clearInterval(interval);
  }, [fetchData]);

  const handleTrigger = async (site) => {
    try {
      await triggerScrape(site);
      fetchData(true);
    } catch (error) {
      alert(`Failed to trigger: ${error.message}`);
    }
  };

  const handleAddSite = async (e) => {
    e.preventDefault();
    try {
      await addSite(newSite);
      setNewSite({ domain: "", listing_url: "" });
      setShowAddForm(false);
      fetchData(true);
    } catch (error) {
      alert(`Failed to add site: ${error.message}`);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 animate-pulse">
        <Activity className="w-12 h-12 text-brand-400 mb-4 animate-spin-slow" />
        <p className="text-zinc-500 font-medium">Loading analytics engine...</p>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-fade-in">
      {/* ── Header & Tabs ─────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <LayoutDashboard className="w-6 h-6 text-brand-400" />
            Scraper Analytics
          </h2>
          <p className="text-sm text-zinc-500">Monitor and manage the ingestion pipeline</p>
        </div>

        <div className="flex items-center gap-2 bg-white/5 p-1 rounded-xl w-fit">
          {[
            { id: "overview", label: "Overview", icon: BarChart3 },
            { id: "history",  label: "History",  icon: History },
            { id: "failures", label: "Failures", icon: AlertCircle },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-medium transition-all ${
                activeTab === tab.id 
                  ? "bg-brand-500 text-white shadow-lg shadow-brand-500/20" 
                  : "text-zinc-400 hover:text-zinc-200 hover:bg-white/5"
              }`}
            >
              <tab.icon className="w-3.5 h-3.5" />
              {tab.label}
            </button>
          ))}
          <div className="w-px h-4 bg-white/10 mx-1" />
          <button 
            onClick={() => fetchData(true)}
            disabled={refreshing}
            className="p-2 text-zinc-500 hover:text-brand-400 transition-colors disabled:opacity-50"
          >
            <RefreshCcw className={`w-4 h-4 ${refreshing ? "animate-spin" : ""}`} />
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
            className="space-y-8"
          >
            {/* Stats Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <StatCard 
                label="Total Products" 
                value={stats?.total_products || 0} 
                icon={Database}
                sub={`Active: ${stats?.active_products || 0}`}
                color="brand"
              />
              <StatCard 
                label="Success Rate" 
                value={`${stats?.success_rate || 0}%`} 
                icon={CheckCircle2}
                sub="Last 50 jobs"
                color="green"
              />
              <StatCard 
                label="Dead Letters" 
                value={stats?.failed_products_count || 0} 
                icon={AlertCircle}
                sub="Requires review"
                color="red"
              />
              <StatCard 
                label="Total Jobs" 
                value={stats?.total_jobs || 0} 
                icon={Clock}
                sub="Lifetime runs"
                color="purple"
              />
            </div>

            {/* Site Management */}
            <div className="glass rounded-3xl p-6">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-lg font-semibold flex items-center gap-2">
                  <Activity className="w-5 h-5 text-brand-400" />
                  Target Site Control
                </h3>
                <button 
                  onClick={() => setShowAddForm(!showAddForm)}
                  className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-brand-500/10 text-brand-400 hover:bg-brand-500 hover:text-white transition-all text-xs font-bold"
                >
                  <Plus className="w-3.5 h-3.5" />
                  Add Site
                </button>
              </div>

              <AnimatePresence>
                {showAddForm && (
                  <motion.form 
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    onSubmit={handleAddSite}
                    className="mb-8 p-6 rounded-2xl bg-white/5 border border-brand-500/20 overflow-hidden"
                  >
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                      <div>
                        <label className="block text-[10px] uppercase tracking-wider text-zinc-500 mb-1.5 font-bold">Domain (e.g. nike.com)</label>
                        <input 
                          required
                          type="text" 
                          placeholder="nike.com"
                          className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-2.5 text-sm focus:border-brand-500 outline-none transition-colors"
                          value={newSite.domain}
                          onChange={e => setNewSite({...newSite, domain: e.target.value.toLowerCase()})}
                        />
                      </div>
                      <div>
                        <label className="block text-[10px] uppercase tracking-wider text-zinc-500 mb-1.5 font-bold">Listing URL (Search Page)</label>
                        <input 
                          required
                          type="url" 
                          placeholder="https://..."
                          className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-2.5 text-sm focus:border-brand-500 outline-none transition-colors"
                          value={newSite.listing_url}
                          onChange={e => setNewSite({...newSite, listing_url: e.target.value})}
                        />
                      </div>
                    </div>
                    <div className="flex justify-end gap-3">
                      <button 
                        type="button"
                        onClick={() => setShowAddForm(false)}
                        className="px-4 py-2 text-xs font-medium text-zinc-400 hover:text-zinc-200 transition-colors"
                      >
                        Cancel
                      </button>
                      <button 
                        type="submit"
                        className="px-6 py-2 bg-brand-500 text-white rounded-lg text-xs font-bold shadow-lg shadow-brand-500/20 hover:shadow-brand-500/40 transition-all"
                      >
                        Register Site
                      </button>
                    </div>
                  </motion.form>
                )}
              </AnimatePresence>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {sites.map((site) => {
                  const lastJob = jobs.find(j => j.site === site.domain);
                  return (
                    <div key={site.domain} className="p-4 rounded-2xl bg-white/5 border border-white/5 flex items-center justify-between group hover:bg-white/[0.07] transition-all">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <Globe className="w-3 h-3 text-zinc-500" />
                          <p className="font-medium text-sm truncate">{site.domain}</p>
                        </div>
                        <p className="text-[10px] text-zinc-500 mt-1 uppercase tracking-wider">
                          {lastJob ? `Last Scraped: ${new Date(lastJob.started_at).toLocaleDateString()}` : 'Never run'}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <a 
                          href={site.listing_url} 
                          target="_blank" 
                          rel="noreferrer"
                          className="w-8 h-8 rounded-full bg-white/5 flex items-center justify-center text-zinc-500 hover:text-zinc-200 hover:bg-white/10 transition-all"
                          title="Open listing URL"
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                        </a>
                        <button 
                          onClick={() => handleTrigger(site.domain)}
                          className="w-8 h-8 rounded-full bg-zinc-800 flex items-center justify-center text-zinc-400 hover:bg-brand-500 hover:text-white transition-all group-hover:scale-110 shadow-lg"
                        >
                          <Play className="w-3.5 h-3.5 fill-current" />
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Quick Job View */}
            <div className="glass rounded-3xl p-6">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-lg font-semibold flex items-center gap-2">
                  <History className="w-5 h-5 text-brand-400" />
                  Recent Activity
                </h3>
                <button onClick={() => setActiveTab("history")} className="text-xs text-brand-400 hover:underline">View all</button>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left">
                  <thead>
                    <tr className="text-zinc-500 text-[10px] uppercase tracking-wider border-b border-white/5">
                      <th className="pb-3 pl-2">Site</th>
                      <th className="pb-3">Started</th>
                      <th className="pb-3">Status</th>
                      <th className="pb-3 text-right pr-2">Scraped</th>
                    </tr>
                  </thead>
                  <tbody className="text-sm">
                    {jobs.slice(0, 5).map((job) => (
                      <tr key={job.id} className="border-b border-white/5 hover:bg-white/5 transition-colors group">
                        <td className="py-4 pl-2 font-medium">{job.site}</td>
                        <td className="py-4 text-zinc-400 text-xs">
                          {new Date(job.started_at).toLocaleString([], { hour: '2-digit', minute: '2-digit', month: 'short', day: 'numeric' })}
                        </td>
                        <td className="py-4">
                          <StatusBadge status={job.status} />
                        </td>
                        <td className="py-4 text-right pr-2 font-mono text-xs">{job.products_scraped}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </motion.div>
        )}

        {activeTab === "history" && (
          <motion.div 
            key="history"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            className="glass rounded-3xl p-6"
          >
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead>
                  <tr className="text-zinc-500 text-[10px] uppercase tracking-wider border-b border-white/5">
                    <th className="pb-3 pl-2">Job ID</th>
                    <th className="pb-3">Site</th>
                    <th className="pb-3">Started</th>
                    <th className="pb-3">Duration</th>
                    <th className="pb-3">Status</th>
                    <th className="pb-3 text-right pr-2">Products</th>
                  </tr>
                </thead>
                <tbody className="text-sm">
                  {jobs.map((job) => {
                    const duration = job.finished_at 
                      ? Math.round((new Date(job.finished_at) - new Date(job.started_at)) / 1000)
                      : null;
                    return (
                      <tr key={job.id} className="border-b border-white/5 hover:bg-white/5 transition-colors">
                        <td className="py-4 pl-2 text-zinc-500 font-mono text-[10px]">#{job.id}</td>
                        <td className="py-4 font-medium">{job.site}</td>
                        <td className="py-4 text-zinc-400 text-xs">
                          {new Date(job.started_at).toLocaleString()}
                        </td>
                        <td className="py-4 text-zinc-500 text-xs">
                          {duration ? `${duration}s` : job.status === 'running' ? '—' : 'n/a'}
                        </td>
                        <td className="py-4">
                          <StatusBadge status={job.status} />
                          {job.error_message && (
                            <p className="text-[10px] text-red-400 mt-1 max-w-[200px] truncate" title={job.error_message}>
                              {job.error_message}
                            </p>
                          )}
                        </td>
                        <td className="py-4 text-right pr-2 font-mono text-xs">{job.products_scraped}</td>
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
            className="space-y-4"
          >
            {deadLetters.length === 0 ? (
              <div className="glass rounded-3xl p-12 text-center">
                <CheckCircle2 className="w-12 h-12 text-green-400 mx-auto mb-4 opacity-50" />
                <p className="text-zinc-400">No failed products detected. The pipeline is healthy!</p>
              </div>
            ) : (
              deadLetters.map((entry, i) => (
                <div key={i} className="glass rounded-2xl p-4 flex flex-col sm:flex-row gap-4 items-start border-l-4 border-red-500/50">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-[10px] font-bold uppercase tracking-tighter px-1.5 py-0.5 rounded bg-red-500/10 text-red-400 border border-red-500/20">
                        {entry.source_site}
                      </span>
                      <span className="text-[10px] text-zinc-500">
                        {new Date(entry.timestamp).toLocaleString()}
                      </span>
                    </div>
                    <p className="text-xs text-zinc-300 font-medium mb-1 truncate" title={entry.product_url}>
                      {entry.product_url}
                    </p>
                    <p className="text-[11px] text-red-400/80 leading-relaxed">
                      Reason: {entry.reason}
                    </p>
                  </div>
                  <a 
                    href={entry.product_url} 
                    target="_blank" 
                    rel="noreferrer"
                    className="shrink-0 px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-[10px] text-zinc-400 hover:text-zinc-200 transition-all"
                  >
                    Inspect Link
                  </a>
                </div>
              ))
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function StatCard({ label, value, icon: Icon, sub, color }) {
  const colorMap = {
    brand: "text-brand-400 bg-brand-500/10 border-brand-500/20",
    green: "text-green-400 bg-green-500/10 border-green-500/20",
    red: "text-red-400 bg-red-500/10 border-red-500/20",
    purple: "text-purple-400 bg-purple-500/10 border-purple-500/20",
  };

  return (
    <div className="glass rounded-2xl p-5 hover:border-white/10 transition-colors group">
      <div className="flex items-center justify-between mb-4">
        <div className={`p-2 rounded-xl border ${colorMap[color]}`}>
          <Icon className="w-5 h-5" />
        </div>
      </div>
      <div>
        <p className="text-3xl font-bold tracking-tight mb-1">{value}</p>
        <p className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">{label}</p>
        {sub && <p className="text-[10px] text-zinc-500 mt-2 font-medium">{sub}</p>}
      </div>
    </div>
  );
}

function StatusBadge({ status }) {
  const styles = {
    running: "bg-blue-500/10 text-blue-400 border-blue-500/20",
    completed: "bg-green-500/10 text-green-400 border-green-500/20",
    failed: "bg-red-500/10 text-red-400 border-red-500/20",
  };

  return (
    <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-tight border ${styles[status] || styles.failed}`}>
      {status}
    </span>
  );
}
