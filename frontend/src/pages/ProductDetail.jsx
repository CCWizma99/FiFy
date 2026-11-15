import useRequest from '../hooks/useRequest';
import FavoriteButton from '../components/FavoriteButton';
import ProductImage from '../components/ProductImage';
import { shareProduct } from '../utils';
import { useState, useCallback } from 'react';
import { ArrowLeft, Share, ExternalLink, Loader2 } from 'lucide-react';
import { useNavigate, useParams } from 'react-router-dom';
import { getProductById } from '../api/search';

export default function ProductDetail() {
  const navigate = useNavigate();
  const { id } = useParams();
  const load = useCallback(signal => getProductById(id, signal), [id]);
  const { data: product, loading, error, retry } = useRequest(id, load);
  const [shareStatus, setShareStatus] = useState(null);
  async function share() {
    try { setShareStatus({ id, text: await shareProduct(product) }); }
    catch (error) { setShareStatus({ id, text: error.message }); }
  }

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
        <p role="alert">{error?.message}</p><button onClick={retry}>Retry</button>
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
          <FavoriteButton product={product} />
          <button aria-label="Share product" onClick={share} className="p-2 bg-white/80 backdrop-blur-md text-navy rounded-full shadow-sm hover:bg-white transition-colors">
            <Share size={20} />
          </button>
        </div>
      </header>

      {/* Main Image */}
      <div className="w-full aspect-[4/5] bg-light lg:max-h-[70vh] flex items-center justify-center overflow-hidden">
        <ProductImage product={product} className="w-full h-full object-contain" />
      </div>

      {shareStatus?.id === id && <p role="status">{shareStatus.text}</p>}
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
            onClick={() => navigate('/results', { state: { type: 'text', query: product.product_name } })}
          >
            Find Similar Items
          </button>
        </div>


      </div>
    </div>
  );
}
