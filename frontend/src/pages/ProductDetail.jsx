import { useState, useEffect } from 'react';
import { ArrowLeft, Heart, Share, ExternalLink, ChevronRight, Loader2 } from 'lucide-react';
import { useNavigate, useParams } from 'react-router-dom';
import { getProductById, getProxyImageUrl } from '../api/search';

export default function ProductDetail() {
  const navigate = useNavigate();
  const { id } = useParams();
  const [product, setProduct] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchProduct() {
      try {
        setLoading(true);
        const data = await getProductById(id);
        setProduct(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    fetchProduct();
  }, [id]);

  if (loading) {
    return (
      <div className="min-h-screen bg-light flex items-center justify-center">
        <Loader2 className="w-10 h-10 text-accent animate-spin" />
      </div>
    );
  }

  if (error || !product) {
    return (
      <div className="min-h-screen bg-light flex flex-col items-center justify-center p-6 text-center">
        <h2 className="text-2xl font-serif font-semibold text-navy mb-4">Product Not Found</h2>
        <button onClick={() => navigate(-1)} className="px-8 py-3 bg-navy text-white rounded-full text-sm font-bold shadow-lg">
          Go Back
        </button>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white pb-24 animate-fade-in">
      {/* Header overlaid on image */}
      <header className="fixed top-0 left-0 right-0 z-40 px-5 py-4 flex items-center justify-between pointer-events-none">
        <button onClick={() => navigate(-1)} className="pointer-events-auto p-2 bg-white/80 backdrop-blur-md text-navy rounded-full shadow-sm hover:bg-white transition-colors">
          <ArrowLeft size={20} />
        </button>
        <div className="flex gap-2 pointer-events-auto">
          <button className="p-2 bg-white/80 backdrop-blur-md text-navy rounded-full shadow-sm hover:text-accent transition-colors">
            <Heart size={20} />
          </button>
          <button className="p-2 bg-white/80 backdrop-blur-md text-navy rounded-full shadow-sm hover:bg-white transition-colors">
            <Share size={20} />
          </button>
        </div>
      </header>

      {/* Main Image */}
      <div className="w-full aspect-[4/5] bg-light lg:max-h-[70vh] flex items-center justify-center overflow-hidden">
        <img 
          src={getProxyImageUrl(product.image_url)} 
          alt={product.product_name} 
          className="w-full h-full object-cover lg:object-contain"
        />
      </div>

      {/* Details */}
      <div className="px-6 py-8 space-y-8 max-w-2xl mx-auto">
        <div className="space-y-2">
          <p className="text-[11px] font-black text-muted tracking-[0.2em] uppercase">{product.brand || product.source_site}</p>
          <h1 className="text-3xl font-serif text-navy tracking-tight leading-tight font-semibold">{product.product_name}</h1>
          <div className="flex items-center gap-3 mt-4">
            <p className="text-2xl font-black text-navy">{product.currency || '$'}{product.price?.toFixed(2)}</p>
            <span className="px-3 py-1 bg-light text-navy text-[10px] font-black uppercase tracking-widest rounded-lg border border-bordercolor">
              {product.source_site}
            </span>
          </div>
        </div>

        {/* Actions */}
        <div className="flex flex-col sm:flex-row gap-4 pt-4">
          <button 
            onClick={() => window.open(product.product_url, '_blank')}
            className="flex-1 bg-navy text-white h-14 rounded-full font-black text-xs uppercase tracking-[0.2em] flex items-center justify-center gap-3 shadow-xl shadow-navy/10 hover:bg-accent transition-all"
          >
            Buy on {product.source_site} <ExternalLink size={16} />
          </button>
          <button 
            className="flex-1 border border-bordercolor text-navy h-14 rounded-full font-black text-xs uppercase tracking-[0.2em] flex items-center justify-center gap-3 hover:bg-light transition-all"
            onClick={() => navigate('/')}
          >
            Find Similar Items
          </button>
        </div>

        {/* Price History */}
        <div className="mt-12 pt-10 border-t border-bordercolor">
          <div className="flex items-center justify-between mb-6">
            <h3 className="font-serif text-xl font-semibold text-navy italic">
              Price Insights
            </h3>
            <span className="text-[10px] font-bold text-accent uppercase tracking-widest">Analytics Dashboard</span>
          </div>
          <div className="h-32 bg-light rounded-[32px] border border-bordercolor flex items-end px-8 py-4 gap-3 relative overflow-hidden shadow-inner">
             {/* Decorative grid */}
             <div className="absolute inset-0 opacity-[0.03]" style={{ backgroundImage: 'radial-gradient(#111 1px, transparent 0)', backgroundSize: '20px 20px' }}></div>
            
            {/* Fake chart bars with some variation */}
            {[45, 65, 85, 55, 95, 75, 100].map((h, i) => (
              <div 
                key={i} 
                className="flex-1 bg-accent/40 rounded-t-xl hover:bg-accent transition-all cursor-pointer relative z-10" 
                style={{ height: `${h}%` }}
                title={`$${(product.price * (h/100 + 0.1)).toFixed(2)}`}
              ></div>
            ))}
          </div>
          <div className="flex justify-between text-[10px] font-black text-muted uppercase tracking-[0.1em] mt-4 px-2">
            <span>Market Low: $24.00</span>
            <span>Current Value</span>
          </div>
        </div>
      </div>
    </div>
  );
}
