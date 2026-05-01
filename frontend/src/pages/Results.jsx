import { useState, useEffect, useCallback } from 'react';
import { ArrowLeft, SlidersHorizontal, Heart, Loader2, AlertCircle } from 'lucide-react';
import { useNavigate, useLocation } from 'react-router-dom';
import { searchByText, searchByImage, getProxyImageUrl } from '../api/search';

export default function Results() {
  const navigate = useNavigate();
  const location = useLocation();
  const { query, file, type } = location.state || {};

  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [queryPreview, setQueryPreview] = useState(null);
  const [activeCategory, setActiveCategory] = useState('All');

  const performSearch = useCallback(async () => {
    if (!type) {
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      let data;
      const filters = {};
      if (activeCategory !== 'All') filters.category = activeCategory;

      if (type === 'text') {
        data = await searchByText(query, filters);
      } else if (type === 'image') {
        // Create preview for query image
        if (!queryPreview) {
          const reader = new FileReader();
          reader.onloadend = () => setQueryPreview(reader.result);
          reader.readAsDataURL(file);
        }
        
        data = await searchByImage(file, filters);
      }
      setProducts(data.results || []);
    } catch (err) {
      console.error('Search failed:', err);
      setError(err.message || 'Something went wrong while searching.');
    } finally {
      setLoading(false);
    }
  }, [query, file, type, activeCategory, queryPreview]);

  useEffect(() => {
    if (!location.state) {
      navigate('/');
      return;
    }
    performSearch();
  }, [location.state, navigate, performSearch]);

  if (loading) {
    return (
      <div className="min-h-screen bg-light flex flex-col items-center justify-center p-6">
        <Loader2 className="w-10 h-10 text-accent animate-spin mb-4" strokeWidth={1.5} />
        <p className="text-navy font-serif italic text-lg tracking-wide">Scouring the fashion world for you...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-light flex flex-col items-center justify-center p-6 text-center">
        <AlertCircle className="w-12 h-12 text-red-400 mb-4" />
        <h2 className="text-2xl font-serif font-semibold text-navy mb-2">Search Interrupted</h2>
        <p className="text-muted max-w-xs mb-8">{error}</p>
        <button 
          onClick={() => navigate('/')}
          className="px-8 py-3 bg-navy text-white rounded-full text-sm font-bold shadow-lg hover:bg-accent transition-all"
        >
          Try Another Search
        </button>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-light pb-24 animate-fade-in">
      {/* Top Bar */}
      <header className="sticky top-0 z-40 bg-white/95 backdrop-blur-md border-b border-bordercolor px-5 md:px-12 py-4 flex items-center justify-between">
        <div className="flex items-center gap-6">
          <button onClick={() => navigate(-1)} className="p-2 -ml-2 text-navy hover:bg-light rounded-full transition-colors">
            <ArrowLeft size={22} />
          </button>
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl overflow-hidden bg-light border border-bordercolor flex items-center justify-center text-muted">
              {type === 'image' && queryPreview ? (
                <img src={queryPreview} alt="Query" className="w-full h-full object-cover" />
              ) : (
                <div className="p-2 text-center text-[10px] font-black uppercase tracking-tighter leading-none">Text Query</div>
              )}
            </div>
            <div className="flex flex-col">
              <span className="text-sm font-bold text-navy tracking-tight">
                {type === 'text' ? `"${query}"` : 'Visual match results'}
              </span>
              <span className="text-[11px] text-muted font-sans uppercase tracking-[0.1em]">{products.length} items discovered</span>
            </div>
          </div>
        </div>
        <button className="p-2.5 -mr-2 text-navy hover:bg-light rounded-full transition-colors border border-bordercolor md:border-none">
          <SlidersHorizontal size={18} />
        </button>
      </header>

      <div className="flex overflow-x-auto gap-3 px-5 md:px-12 py-6 hide-scrollbar">
        {['All', 'Tops', 'Bottoms', 'Dresses', 'Outerwear', 'Footwear', 'Innerwear', 'Bags', 'Accessories', 'Activewear', 'Other'].map(cat => (
          <button 
            key={cat} 
            onClick={() => setActiveCategory(cat)}
            className={`flex-none px-6 py-2 border rounded-full text-[11px] font-bold uppercase tracking-widest transition-all shadow-sm ${activeCategory === cat ? 'bg-navy text-white border-navy' : 'bg-white border-bordercolor text-muted hover:border-accent hover:text-navy'}`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Grid */}
      <main className="px-5 md:px-12 columns-2 lg:columns-4 gap-6 space-y-6 max-w-7xl mx-auto">
        {products.length === 0 ? (
          <div className="col-span-full py-32 text-center">
            <p className="text-muted font-serif italic text-xl">No matches found in our current collection.</p>
          </div>
        ) : (
          products.map((p, idx) => (
            <div 
              key={p.id} 
              onClick={() => navigate(`/product/${p.id}`)}
              className={`relative break-inside-avoid mb-6 bg-white rounded-3xl overflow-hidden cursor-pointer shadow-sm group transition-all duration-300 hover:-translate-y-1 hover:shadow-xl hover:shadow-navy/5 border border-bordercolor ${idx === 0 ? 'ring-2 ring-accent ring-offset-2 ring-offset-light' : ''}`}
            >
              {idx === 0 && (
                <div className="absolute top-3 left-3 z-10 bg-accent text-white text-[9px] font-black uppercase tracking-[0.2em] px-2.5 py-1 rounded-lg shadow-md">
                  Best Match
                </div>
              )}
              <div className="absolute top-3 right-3 z-10 bg-white/90 backdrop-blur-sm p-2 rounded-full text-navy hover:text-accent transition-colors shadow-sm">
                <Heart size={14} />
              </div>
              <div className="aspect-[3/4] bg-light overflow-hidden">
                <img src={getProxyImageUrl(p.image_url)} alt={p.product_name} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700" loading="lazy" />
              </div>
              <div className="p-4">
                <div className="flex items-center justify-between mb-1.5">
                  <p className="text-[10px] font-black text-muted tracking-[0.1em] uppercase">{p.brand || p.source_site}</p>
                  <p className="text-[10px] px-2 py-0.5 rounded-md bg-light text-navy font-bold uppercase">{p.source_site}</p>
                </div>
                <p className="text-[13px] font-medium text-navy leading-tight line-clamp-2 mb-2">{p.product_name}</p>
                <p className="text-sm font-black text-navy">{p.currency || '$'}{p.price?.toFixed(2)}</p>
              </div>
            </div>
          ))
        )}
      </main>
    </div>
  );
}
