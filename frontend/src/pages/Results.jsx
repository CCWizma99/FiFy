import { ArrowLeft, SlidersHorizontal, Heart } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function Results() {
  const navigate = useNavigate();
  
  // Dummy data based on the mockups
  const products = [
    { id: 1, brand: 'ZARA', price: '$89.90', img: 'https://images.unsplash.com/photo-1515372039744-b8f02a3ae446?auto=format&fit=crop&w=400&q=80', isBestMatch: true },
    { id: 2, brand: 'ASOS DESIGN', price: '$54.00', img: 'https://images.unsplash.com/photo-1539008835657-9e8e9680c956?auto=format&fit=crop&w=400&q=80' },
    { id: 3, brand: 'H&M', price: '$39.99', img: 'https://images.unsplash.com/photo-1496747611176-843222e1e57c?auto=format&fit=crop&w=400&q=80' },
    { id: 4, brand: 'MANGO', price: '$119.00', img: 'https://images.unsplash.com/photo-1550639525-c97d455acf70?auto=format&fit=crop&w=400&q=80' },
  ];

  return (
    <div className="min-h-screen bg-cream-100 pb-24 pt-safe animate-fade-in">
      {/* Top Bar */}
      <header className="sticky top-0 z-40 bg-white/90 backdrop-blur-md border-b border-cream-300 px-4 py-3 flex items-center justify-between">
        <button onClick={() => navigate(-1)} className="p-2 -ml-2 text-charcoal-900 hover:bg-cream-200 rounded-full transition-colors">
          <ArrowLeft size={24} />
        </button>
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg overflow-hidden bg-cream-200 border border-cream-300">
            <img src="https://images.unsplash.com/photo-1515372039744-b8f02a3ae446?auto=format&fit=crop&w=100&q=80" alt="Query" className="w-full h-full object-cover" />
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-semibold text-charcoal-900">Similar items found</span>
            <span className="text-xs text-charcoal-800/60">4 results</span>
          </div>
        </div>
        <button className="p-2 -mr-2 text-charcoal-900 hover:bg-cream-200 rounded-full transition-colors">
          <SlidersHorizontal size={20} />
        </button>
      </header>

      {/* Filter Chips */}
      <div className="flex overflow-x-auto gap-2 px-4 py-4 hide-scrollbar">
        {['Price Range', 'Color', 'Category', 'Site'].map(filter => (
          <button key={filter} className="flex-none px-4 py-1.5 bg-white border border-cream-300 rounded-full text-xs font-medium text-charcoal-800 hover:border-dustyrose-400 transition-colors shadow-sm">
            {filter} <span className="ml-1 text-charcoal-800/40">▼</span>
          </button>
        ))}
      </div>

      {/* Masonry Grid (Simulated with columns) */}
      <main className="px-4 columns-2 lg:columns-4 gap-4 space-y-4 max-w-6xl mx-auto">
        {products.map((p) => (
          <div 
            key={p.id} 
            onClick={() => navigate(`/product/${p.id}`)}
            className={`relative break-inside-avoid mb-4 bg-white rounded-2xl overflow-hidden cursor-pointer shadow-sm group transition-transform duration-300 hover:-translate-y-1 ${p.isBestMatch ? 'ring-2 ring-dustyrose-400 ring-offset-2 ring-offset-cream-100' : 'border border-cream-200'}`}
          >
            {p.isBestMatch && (
              <div className="absolute top-2 left-2 z-10 bg-dustyrose-500 text-white text-[10px] font-bold uppercase tracking-wider px-2 py-1 rounded-md shadow-sm">
                Best Match
              </div>
            )}
            <div className="absolute top-2 right-2 z-10 bg-white/80 backdrop-blur-sm p-1.5 rounded-full text-charcoal-900 hover:text-dustyrose-500 transition-colors">
              <Heart size={16} />
            </div>
            <div className="aspect-[3/4] bg-cream-200 overflow-hidden">
              <img src={p.img} alt={p.brand} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" loading="lazy" />
            </div>
            <div className="p-3">
              <p className="text-xs font-bold text-charcoal-800/60 tracking-widest uppercase mb-0.5">{p.brand}</p>
              <p className="text-sm font-semibold text-charcoal-900">{p.price}</p>
            </div>
          </div>
        ))}
      </main>
    </div>
  );
}
