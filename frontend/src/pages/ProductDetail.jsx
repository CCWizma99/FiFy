import { ArrowLeft, Heart, Share, ExternalLink, ChevronRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function ProductDetail() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-white pb-24 animate-fade-in">
      {/* Header overlaid on image */}
      <header className="fixed top-0 left-0 right-0 z-40 px-4 py-4 flex items-center justify-between pointer-events-none">
        <button onClick={() => navigate(-1)} className="pointer-events-auto p-2 bg-white/80 backdrop-blur-md text-charcoal-900 rounded-full shadow-sm hover:bg-white transition-colors">
          <ArrowLeft size={20} />
        </button>
        <div className="flex gap-2 pointer-events-auto">
          <button className="p-2 bg-white/80 backdrop-blur-md text-charcoal-900 rounded-full shadow-sm hover:text-dustyrose-500 transition-colors">
            <Heart size={20} />
          </button>
          <button className="p-2 bg-white/80 backdrop-blur-md text-charcoal-900 rounded-full shadow-sm hover:bg-white transition-colors">
            <Share size={20} />
          </button>
        </div>
      </header>

      {/* Main Image */}
      <div className="w-full aspect-[4/5] bg-cream-200 lg:max-h-[60vh] lg:object-contain overflow-hidden">
        <img 
          src="https://images.unsplash.com/photo-1515372039744-b8f02a3ae446?auto=format&fit=crop&w=800&q=80" 
          alt="Product" 
          className="w-full h-full object-cover lg:object-contain"
        />
      </div>

      {/* Details */}
      <div className="px-6 py-6 space-y-6 max-w-2xl mx-auto">
        <div className="space-y-1">
          <p className="text-xs font-bold text-charcoal-800/60 tracking-widest uppercase">ZARA</p>
          <h1 className="text-2xl font-serif text-charcoal-900 tracking-tight leading-tight">Flowy Linen Blend Dress</h1>
          <p className="text-xl font-medium text-charcoal-900 mt-2">$89.90</p>
        </div>

        {/* Sizes */}
        <div className="space-y-3">
          <div className="flex justify-between items-center">
            <span className="text-sm font-semibold text-charcoal-900">Select Size</span>
            <span className="text-xs text-charcoal-800/60 underline cursor-pointer hover:text-charcoal-900">Size Guide</span>
          </div>
          <div className="flex gap-3">
            {['XS', 'S', 'M', 'L'].map(size => (
              <button key={size} className="w-12 h-12 rounded-full border border-cream-300 flex items-center justify-center font-medium text-charcoal-900 hover:border-charcoal-900 transition-colors bg-white">
                {size}
              </button>
            ))}
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-3 pt-2">
          <button className="btn-primary flex-1">
            View on Site <ExternalLink size={16} />
          </button>
          <button className="btn-secondary flex-1" onClick={() => navigate('/results')}>
            Find Similar
          </button>
        </div>

        {/* Price History */}
        <div className="mt-8 pt-8 border-t border-cream-200">
          <h3 className="font-semibold text-charcoal-900 mb-4 flex items-center justify-between">
            Price History <ChevronRight size={16} className="text-charcoal-800/40" />
          </h3>
          <div className="h-24 bg-cream-50 rounded-xl border border-cream-200 flex items-end px-4 py-2 gap-2">
            {/* Fake chart bars */}
            {[40, 60, 80, 50, 90, 70, 100].map((h, i) => (
              <div key={i} className="flex-1 bg-dustyrose-400/50 rounded-t-sm hover:bg-dustyrose-500 transition-colors cursor-pointer" style={{ height: `${h}%` }}></div>
            ))}
          </div>
          <div className="flex justify-between text-xs text-charcoal-800/60 mt-2 px-1">
            <span>30 days ago</span>
            <span>Today</span>
          </div>
        </div>
      </div>
    </div>
  );
}
