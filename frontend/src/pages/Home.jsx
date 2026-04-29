import { useState, useEffect } from 'react';
import { Search, Upload, Heart } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { getAllProducts, getProxyImageUrl } from '../api/search';

export default function Home() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState("Women's fashion");
  const [activeCat, setActiveCat] = useState('All');
  const [activeFilter, setActiveFilter] = useState('Best match');
  
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadTrending() {
      try {
        setLoading(true);
        // Map UI labels to backend filter values
        const genderMap = {
          "Women's fashion": "women",
          "Men's fashion": "men",
          "Neutral fashion": "neutral"
        };
        
        const filters = {
          category: activeCat === 'All' ? null : activeCat,
          gender: genderMap[activeTab] || null
        };

        const data = await getAllProducts(8, filters);
        setProducts(data.map(p => ({ ...p, liked: false })));
      } catch (err) {
        console.error("Failed to load trending products:", err);
      } finally {
        setLoading(false);
      }
    }
    loadTrending();
  }, [activeTab, activeCat]);

  const toggleHeart = (e, id) => {
    e.stopPropagation();
    setProducts(products.map(p => p.id === id ? { ...p, liked: !p.liked } : p));
  };

  const categories = ['All', 'Tops', 'Dresses', 'Skirts', 'Jackets & coats', 'Trousers', 'Shoes', 'Bags', 'Accessories'];

  return (
    <div className="flex flex-col animate-fade-in">
      {/* Hero */}
      <div className="bg-navy px-5 md:px-12 py-12 md:py-[72px] pb-[80px] md:pb-[100px] text-center relative overflow-hidden">
        <div className="absolute top-[-80px] left-1/2 -translate-x-1/2 w-[600px] h-[600px] rounded-full pointer-events-none" style={{ background: 'radial-gradient(circle, rgba(212,175,55,0.15) 0%, transparent 70%)' }}></div>
        <div className="inline-block text-[11px] tracking-[2.5px] uppercase text-[#D4AF37] mb-5 font-sans">Seen it? Find it.</div>
        <h1 className="font-serif text-4xl md:text-[56px] font-medium text-white leading-[1.15] max-w-[640px] mx-auto mb-4 tracking-tight">
          Here you find all the clothing items you <em className="text-[#D4AF37] not-italic italic">couldn't find.</em>
        </h1>
        <p className="text-[15px] text-white/50 mb-10 font-light max-w-xl mx-auto font-sans">Upload a photo or describe what you saw — we'll find the closest match with price and where to buy.</p>
        
        <div className="max-w-2xl mx-auto relative group flex items-center w-full">
          <div className="absolute inset-y-0 left-5 flex items-center pointer-events-none text-[#aaa] group-focus-within:text-accent transition-colors">
            <Search size={18} strokeWidth={2} />
          </div>
          <input 
            type="text" 
            placeholder="Describe what you saw (e.g., flowy beige linen dress)..." 
            className="w-full bg-white rounded-full py-[14px] sm:py-[16px] pl-[40px] sm:pl-[48px] pr-[64px] sm:pr-[150px] text-[13px] sm:text-[14px] text-navy placeholder:text-[#aaa] outline-none shadow-sm transition-shadow focus:ring-2 ring-[#D4AF37]/50 font-sans"
            onKeyDown={(e) => {
              if (e.key === 'Enter' && e.target.value.trim()) {
                navigate('/results', { state: { query: e.target.value, type: 'text' } });
              }
            }}
          />
          <div className="absolute inset-y-0 right-1.5 flex items-center">
            <label className="flex items-center justify-center gap-2 px-3 sm:px-5 py-[8px] sm:py-[10px] bg-accent hover:bg-[#c4a133] text-white rounded-full text-[13px] font-medium transition-colors cursor-pointer border-none shadow-sm">
              <Upload size={14} strokeWidth={2} /> 
              <span className="hidden sm:inline">Upload photo</span>
              <input 
                type="file" 
                className="hidden" 
                accept="image/*" 
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) {
                    navigate('/results', { state: { file, type: 'image' } });
                  }
                }}
              />
            </label>
          </div>
        </div>
      </div>
      
      {/* Wave */}
      <div className="h-10 bg-navy" style={{ clipPath: 'ellipse(60% 100% at 50% 0%)' }}></div>

      <main className="px-5 md:px-12 py-10 max-w-7xl mx-auto w-full">
        {/* Shop Items Tabs */}
        <div className="text-[15px] font-medium text-text mb-3.5 font-sans">Shop for items you like</div>
        <div className="flex overflow-x-auto gap-2 mb-5 hide-scrollbar whitespace-nowrap pb-1">
          {["Neutral fashion", "Women's fashion", "Men's fashion"].map(t => (
            <button 
              key={t}
              onClick={() => setActiveTab(t)}
              className={`px-4 py-1.5 rounded-[18px] border text-[12px] font-sans transition-colors cursor-pointer ${activeTab === t ? 'bg-navy-2 text-white border-navy-2' : 'bg-card text-muted border-bordercolor hover:border-accent hover:text-accent'}`}
            >
              {t}
            </button>
          ))}
        </div>

        {/* Categories Row */}
        <div className="flex gap-3.5 overflow-x-auto pb-2 mb-9 hide-scrollbar">
          {categories.map((c) => (
            <div key={c} onClick={() => setActiveCat(c)} className="shrink-0 flex flex-col items-center gap-1.5 cursor-pointer group">
              <div className={`w-[68px] h-[76px] rounded-[14px] flex items-center justify-center transition-colors ${activeCat === c ? 'border-2 border-navy-2 bg-[#fcfaf5]' : 'border-[1.5px] border-bordercolor bg-light group-hover:border-accent group-hover:bg-[#fcfaf5]'}`}>
                <svg width="28" height="28" viewBox="0 0 40 40" fill="#222222" opacity={activeCat === c ? "0.5" : "0.25"}>
                  <path d="M10 10 L16 6 L24 6 L30 10 L26 16 L14 16 Z M14 16 L26 16 L26 36 L14 36 Z"/>
                </svg>
              </div>
              <div className="text-[11px] text-muted text-center font-sans">{c}</div>
            </div>
          ))}
        </div>

        {/* Filters & Title */}
        <div className="flex flex-col md:flex-row md:items-center justify-between mb-3.5 gap-4">
          <div className="text-[15px] font-medium text-text font-sans m-0">Trending products</div>
          <div className="flex flex-wrap gap-[7px]">
            {['All', 'Under $30', 'Best match', 'New in', 'On sale'].map(f => (
              <button 
                key={f}
                onClick={() => setActiveFilter(f)}
                className={`px-[14px] py-[5px] rounded-[16px] border text-[11.5px] font-sans transition-colors cursor-pointer ${activeFilter === f ? 'border-navy-3 text-navy-3 bg-light font-medium' : 'bg-card text-muted border-bordercolor hover:border-accent hover:text-accent'}`}
              >
                {f}
              </button>
            ))}
          </div>
        </div>

        {/* Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-[18px] mt-4 mb-12 min-h-[400px]">
          {loading ? (
            <div className="col-span-full flex items-center justify-center py-20 text-muted font-serif italic text-lg">
              Curating latest trends...
            </div>
          ) : products.length === 0 ? (
            <div className="col-span-full flex items-center justify-center py-20 text-muted font-serif italic text-lg">
              No products found in the database.
            </div>
          ) : products.map((p, idx) => (
            <div 
              key={p.id} 
              onClick={() => navigate(`/product/${p.id}`)}
              className={`bg-card rounded-[16px] border overflow-hidden cursor-pointer relative transition-all duration-200 hover:-translate-y-[3px] hover:shadow-[0_8px_32px_rgba(15,32,68,0.1)] ${idx === 0 ? 'border-2 border-navy-2 shadow-sm' : 'border-bordercolor'}`}
            >
              {idx === 0 && (
                <div className="absolute top-[10px] left-[10px] bg-navy text-white text-[9.5px] px-[9px] py-[3px] rounded-lg z-10 font-medium font-sans uppercase tracking-wider">Editor's Pick</div>
              )}
              <div className="w-full h-[220px] bg-light flex items-center justify-center relative overflow-hidden">
                <img 
                  src={getProxyImageUrl(p.image_url)} 
                  alt={p.product_name}
                  className="w-full h-full object-cover transition-transform duration-500 hover:scale-105"
                  onError={(e) => { e.target.src = 'https://via.placeholder.com/300x400?text=No+Image'; }}
                />
                <button 
                  onClick={(e) => toggleHeart(e, p.id)}
                  className="absolute top-[9px] right-[9px] w-7 h-7 rounded-full bg-white/95 flex items-center justify-center border border-bordercolor transition-colors hover:border-[#e06080] cursor-pointer"
                >
                  <Heart size={12} strokeWidth={2} fill={p.liked ? '#e06080' : 'none'} color={p.liked ? '#e06080' : '#bbb'} />
                </button>
              </div>
              <div className="p-3 pb-3.5">
                <div className="text-[9.5px] text-muted mb-[3px] uppercase tracking-[0.6px] font-sans font-bold">{p.brand || p.source_site}</div>
                <div className="text-[12.5px] text-text mb-2 leading-[1.35] line-clamp-2 font-sans font-medium h-[34px]">{p.product_name}</div>
                <div className="flex items-center justify-between">
                  <div className="flex items-baseline">
                    <span className="text-[13px] font-bold text-navy font-sans">{p.currency || '$'}{p.price?.toFixed(2)}</span>
                  </div>
                  <div className="text-[9.5px] px-[9px] py-[3px] rounded-lg bg-light text-navy-2 font-black font-sans uppercase tracking-tighter">{p.source_site}</div>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Promo */}
        <div className="bg-navy rounded-[20px] p-6 sm:p-10 text-center mb-12 relative overflow-hidden">
          <div className="absolute top-[-60px] right-[-60px] w-[240px] h-[240px] rounded-full pointer-events-none" style={{ background: 'radial-gradient(circle, rgba(212,175,55,0.2) 0%, transparent 70%)' }}></div>
          <div className="text-[11px] text-white/45 mb-2 tracking-[1px] font-sans">US$3.99 / month</div>
          <h3 className="font-serif text-[30px] font-medium text-white mb-2">Exclusive coupons & discounts.</h3>
          <p className="text-[13px] text-white/55 mb-6 font-light font-sans">Personalised style recommendations based on your favourite influencers</p>
          <button className="bg-white text-navy px-8 py-3 rounded-[24px] text-[13px] font-medium transition-colors hover:bg-light border-none cursor-pointer font-sans">Sign up now</button>
        </div>

        {/* Trending Searches */}
        <div className="text-[15px] font-medium text-text font-sans">Trending searches</div>
        <div className="flex flex-wrap gap-2 mt-3 mb-10">
          {['Shoulder pad', 'Cut out top', 'Three piece swimsuit', 'Knit sets', 'Crop top', 'Sequin dress', 'Charm bracelet', 'Floral print dress', 'Cut out dress', 'Crochet knit', 'Wide leg pants', 'Sequin skirt', 'Wrap around top', 'Sequin top', 'Tie dye print', 'Sheer top', 'Puff sleeves', 'Bubblegum pink', 'Hoop earrings', 'Satin slip dress', 'Linen blazer', 'Cargo trousers'].map(t => (
            <button key={t} className="px-[15px] py-1.5 rounded-[17px] border border-bordercolor bg-card text-[12px] text-muted font-sans transition-colors hover:border-navy-2 hover:text-navy-2 hover:bg-light cursor-pointer">
              {t}
            </button>
          ))}
        </div>

        <div className="border-t border-bordercolor pt-7 mb-8">
          <div className="text-[13px] text-muted mb-1.5 font-sans">Tell us what you think about Fify</div>
          <div className="text-[12px] text-[#aaa] mb-[18px] font-sans">Please click <a href="#" className="text-accent no-underline hover:underline">here</a> to drop us a message</div>
          <div className="text-[13px] text-muted mb-2.5 font-sans">Follow us on social media</div>
          <div className="flex gap-2.5 mt-2.5">
            {['f', 't', 'in', 'ig'].map((label, i) => (
              <button key={i} className="w-[30px] h-[30px] rounded-full border border-bordercolor bg-card flex items-center justify-center text-muted transition-colors hover:border-navy-2 hover:text-navy-2 cursor-pointer text-[11px] font-sans">
                {label}
              </button>
            ))}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-bordercolor px-5 md:px-12 py-7 flex flex-col md:flex-row items-center justify-between bg-card gap-3.5 font-sans">
        <div className="font-serif text-[22px] font-semibold text-navy">fi<span className="text-accent">f</span>y</div>
        <div className="flex flex-wrap justify-center gap-4 sm:gap-5">
          {['About', 'Privacy', 'Terms', 'Contact'].map(l => (
            <a key={l} href="#" className="text-[12px] text-muted hover:text-navy-2 no-underline">{l}</a>
          ))}
        </div>
        <div className="text-[11px] text-[#c0c8d8]">© 2026 Fify. All rights reserved.</div>
      </footer>
    </div>
  );
}
