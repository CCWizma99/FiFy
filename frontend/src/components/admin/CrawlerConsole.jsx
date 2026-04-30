import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Terminal, 
  X, 
  Pause, 
  Play, 
  Square, 
  ChevronRight, 
  Activity,
  Globe
} from "lucide-react";
import { pauseCrawl, resumeCrawl, stopCrawl } from "../../api/admin";

export default function CrawlerConsole({ site, onClose }) {
  const [logs, setLogs] = useState([]);
  const [status, setStatus] = useState("crawling"); // crawling, paused, stopped
  const [currentUrl, setCurrentUrl] = useState("");
  const scrollRef = useRef(null);
  const ws = useRef(null);

  useEffect(() => {
    // Connect to WebSocket
    ws.current = new WebSocket(`ws://localhost:8000/admin/ws/logs/${site.id}`);

    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === "info") {
        setLogs(prev => [...prev.slice(-100), data]);
        if (data.url) setCurrentUrl(data.url);
      } else if (data.type === "status") {
        setStatus(data.message);
      }
    };

    return () => {
      if (ws.current) ws.current.close();
    };
  }, [site.id]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  const handlePause = async () => {
    try {
      await pauseCrawl(site.id);
      setStatus("paused");
    } catch (err) {
      console.error(err);
    }
  };

  const handleResume = async () => {
    try {
      await resumeCrawl(site.id);
      setStatus("crawling");
    } catch (err) {
      console.error(err);
    }
  };

  const handleStop = async () => {
    try {
      await stopCrawl(site.id);
      setStatus("stopped");
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <motion.div 
      initial={{ opacity: 0, scale: 0.95, y: 20 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.95, y: 20 }}
      className="fixed bottom-6 right-6 w-full max-w-2xl bg-navy rounded-[32px] shadow-2xl border border-white/10 overflow-hidden z-50 flex flex-col h-[500px]"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-8 py-6 bg-white/5 border-b border-white/5">
        <div className="flex items-center gap-4">
          <div className={`p-2 rounded-xl ${status === 'crawling' ? 'bg-accent animate-pulse' : 'bg-white/10'}`}>
            <Terminal className="w-5 h-5 text-white" />
          </div>
          <div>
            <h3 className="text-white font-serif text-lg font-semibold flex items-center gap-2">
              Live Indexing: <span className="text-accent italic">{site.domain}</span>
            </h3>
            <p className="text-[10px] text-white/40 uppercase tracking-[0.2em] font-black flex items-center gap-2">
              <Activity className="w-3 h-3" />
              Status: {status}
            </p>
          </div>
        </div>
        <button onClick={onClose} className="p-2 text-white/40 hover:text-white transition-colors">
          <X className="w-6 h-6" />
        </button>
      </div>

      {/* Current URL Bar */}
      <div className="px-8 py-3 bg-black/20 flex items-center gap-3 border-b border-white/5">
        <Globe className="w-3.5 h-3.5 text-white/30" />
        <span className="text-[11px] text-white/60 font-mono truncate flex-1">
          {currentUrl || "Initializing discovery..."}
        </span>
      </div>

      {/* Log Terminal */}
      <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-8 font-mono text-[12px] leading-relaxed space-y-2 scrollbar-hide"
      >
        {logs.map((log, i) => (
          <div key={i} className="flex gap-3 text-white/70">
            <span className="text-accent opacity-50 shrink-0">[{new Date().toLocaleTimeString([], { hour12: false })}]</span>
            <span className={log.message.includes("Indexed") ? "text-green-400 font-bold" : ""}>
              {log.message}
            </span>
          </div>
        ))}
        {logs.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-white/20 italic">
            Waiting for spider connection...
          </div>
        )}
      </div>

      {/* Footer Controls */}
      <div className="px-8 py-6 bg-white/5 border-t border-white/5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          {status === "paused" ? (
            <button 
              onClick={handleResume}
              className="flex items-center gap-2 px-6 py-2.5 bg-green-500 text-white rounded-full text-[11px] font-black uppercase tracking-widest shadow-lg shadow-green-500/20 hover:scale-105 transition-all"
            >
              <Play className="w-3 h-3 fill-current" />
              Resume
            </button>
          ) : (
            <button 
              onClick={handlePause}
              disabled={status === "stopped"}
              className="flex items-center gap-2 px-6 py-2.5 bg-white/10 text-white rounded-full text-[11px] font-black uppercase tracking-widest hover:bg-white/20 transition-all disabled:opacity-30"
            >
              <Pause className="w-3 h-3 fill-current" />
              Pause
            </button>
          )}
          <button 
            onClick={handleStop}
            disabled={status === "stopped"}
            className="flex items-center gap-2 px-6 py-2.5 bg-red-500/10 text-red-400 rounded-full text-[11px] font-black uppercase tracking-widest hover:bg-red-500/20 transition-all disabled:opacity-30"
          >
            <Square className="w-3 h-3 fill-current" />
            Stop
          </button>
        </div>

        <div className="flex items-center gap-2 text-[10px] text-white/30 uppercase tracking-widest font-bold">
          <ChevronRight className="w-3 h-3 text-accent" />
          Queue: Active
        </div>
      </div>
    </motion.div>
  );
}
