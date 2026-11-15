import useRequest from "../../hooks/useRequest";
import ProductImage from "../ProductImage";
import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Search,
  Package,
  ExternalLink,
  Copy,
  Check,
  Image as ImageIcon,
  Tag,
  DollarSign,
  Globe,
  Info,
  ChevronRight,
} from "lucide-react";
import { getAllProducts } from "../../api/search";

export default function ProductsTab() {
  const [query, setQuery] = useState("");
  const [selection, setSelection] = useState(null);
  const [copiedId, setCopiedId] = useState(null);
  const load = useCallback(signal => getAllProducts(50, {}, query, signal), [query]);
  const { data, loading, error, retry } = useRequest(query, load, 500);
  const products = Array.isArray(data) ? data : data?.results || [];
  const selectedProduct = selection?.data === data ? products.find(product => product.id === selection.id) || null : null;

  const copyToClipboard = async (text, id) => {
    try { await navigator.clipboard.writeText(text); setCopiedId(id); }
    catch { setCopiedId('failed'); }
  };

  return (
    <div className="space-y-8">
      {error && <div role="alert">{error.message} <button onClick={retry}>Retry</button></div>}
      {copiedId === "failed" && <p role="alert">Could not copy ID.</p>}
      {/* Search Bar */}
      <div className="relative group">
        <Search className="absolute left-5 top-1/2 -translate-y-1/2 w-5 h-5 text-muted group-focus-within:text-accent transition-colors" />
        <input
          type="text"
          placeholder="Search products semantically (e.g. 'blue silk dress')..."
          className="w-full bg-white border border-bordercolor rounded-3xl pl-14 pr-6 py-5 text-sm focus:border-accent outline-none transition-all shadow-sm group-focus-within:shadow-md"
          value={query}
          onChange={(e) => { setQuery(e.target.value); setSelection(null); }}
        />
        {loading && (
          <div className="absolute right-5 top-1/2 -translate-y-1/2">
            <div className="w-5 h-5 border-2 border-accent border-t-transparent rounded-full animate-spin" />
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 h-[calc(100vh-320px)] min-h-[600px]">
        {/* Product List */}
        <div className="lg:col-span-2 flex flex-col min-h-0">
          <div className="flex items-center justify-between mb-4 px-2 flex-shrink-0">
            <h3 className="text-lg font-serif font-semibold text-navy flex items-center gap-2">
              <Package className="w-5 h-5 text-accent" />
              Inventory <span className="text-muted font-sans text-xs font-normal">({products.length} items)</span>
            </h3>
          </div>

          <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar space-y-4">
            <div className="grid grid-cols-1 gap-4">
            {products.map((product) => (
              <motion.div
                layout
                key={product.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                onClick={() => setSelection({ id: product.id, data })}
                className={`flex items-center gap-4 p-4 rounded-2xl bg-white border transition-all cursor-pointer group ${
                  selectedProduct?.id === product.id ? "border-accent ring-1 ring-accent/20" : "border-bordercolor hover:border-accent/30 hover:shadow-md"
                }`}
              >
                <div className="w-16 h-16 rounded-xl overflow-hidden bg-light flex-shrink-0 border border-bordercolor">
                  <ProductImage
                    product={product}
                    alt={product.product_name}
                    className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500"
                  />
                </div>
                <div className="flex-1 min-w-0">
                  <h4 className="font-bold text-navy text-sm truncate">{product.product_name}</h4>
                  <div className="flex items-center gap-3 mt-1">
                    <span className="text-accent font-bold text-xs">LKR {product.price?.toLocaleString()}</span>
                    <span className="text-[10px] text-muted uppercase tracking-widest bg-light px-2 py-0.5 rounded">{product.source_site}</span>
                  </div>
                </div>
                <ChevronRight className={`w-4 h-4 text-muted transition-transform ${selectedProduct?.id === product.id ? "rotate-90 text-accent" : "group-hover:translate-x-1"}`} />
              </motion.div>
            ))}

            {products.length === 0 && !loading && (
              <div className="py-20 text-center bg-white rounded-3xl border border-dashed border-bordercolor">
                <Package className="w-12 h-12 text-muted/30 mx-auto mb-4" />
                <p className="text-muted font-medium italic">No products found matching your search.</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Detailed View */}
        <div className="lg:col-span-1 min-h-0">
          <div className="h-full overflow-y-auto pr-2 custom-scrollbar">
          <AnimatePresence mode="wait">
            {selectedProduct ? (
              <motion.div
                key={selectedProduct.id}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                className="bg-white rounded-[32px] border border-bordercolor shadow-xl overflow-hidden mb-4"
              >
                <div className="aspect-square relative group">
                  <ProductImage
                    product={selectedProduct}
                    alt={selectedProduct.product_name}
                    className="w-full h-full object-cover"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex items-end p-6">
                    <a
                      href={selectedProduct.product_url}
                      target="_blank"
                      rel="noreferrer"
                      className="flex items-center gap-2 text-white text-xs font-bold uppercase tracking-widest hover:underline"
                    >
                      Visit Product Page <ExternalLink className="w-3 h-3" />
                    </a>
                  </div>
                </div>

                <div className="p-8 space-y-6">
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-[10px] font-black text-accent uppercase tracking-[0.2em]">{selectedProduct.source_site}</span>
                      <button
                        onClick={() => copyToClipboard(selectedProduct.id, 'id')}
                        className="text-muted hover:text-navy transition-colors flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider"
                      >
                        {copiedId === 'id' ? <Check className="w-3 h-3 text-green-500" /> : <Copy className="w-3 h-3" />}
                        {copiedId === 'id' ? 'Copied' : 'ID'}
                      </button>
                    </div>
                    <h2 className="text-2xl font-serif font-semibold text-navy leading-tight">{selectedProduct.product_name}</h2>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <DetailItem icon={DollarSign} label="Price" value={`LKR ${selectedProduct.price?.toLocaleString()}`} />
                    <DetailItem icon={Tag} label="Category" value={selectedProduct.category || "N/A"} />
                    <DetailItem icon={Info} label="Gender" value={selectedProduct.gender || "Neutral"} />
                    <DetailItem icon={Globe} label="Source" value={selectedProduct.source_site} />
                  </div>

                  <div className="pt-6 border-t border-bordercolor">
                    <p className="text-[10px] font-black text-muted uppercase tracking-widest mb-4">Metadata Payload</p>
                    <div className="bg-light rounded-2xl p-4 overflow-x-auto">
                      <pre className="text-[10px] text-muted font-mono leading-relaxed">
                        {JSON.stringify(selectedProduct, null, 2)}
                      </pre>
                    </div>
                  </div>

                  <a
                    href={selectedProduct.product_url}
                    target="_blank"
                    rel="noreferrer"
                    className="w-full py-4 rounded-full bg-navy text-white text-xs font-black uppercase tracking-[0.2em] flex items-center justify-center gap-2 hover:bg-accent transition-all shadow-lg shadow-navy/20"
                  >
                    Open Original Link <ExternalLink className="w-4 h-4" />
                  </a>
                </div>
              </motion.div>
            ) : (
              <div className="bg-white/50 border border-dashed border-bordercolor rounded-[32px] p-12 text-center h-[600px] flex flex-col items-center justify-center">
                <div className="p-6 rounded-full bg-light text-muted mb-6">
                  <ImageIcon className="w-10 h-10" strokeWidth={1} />
                </div>
                <h4 className="text-lg font-serif font-medium text-navy mb-2">No product selected</h4>
                <p className="text-muted text-sm max-w-[200px]">Select a product from the list to view full details and metadata.</p>
              </div>
            )}
          </AnimatePresence>
          </div>
        </div>
      </div>

      <style dangerouslySetInnerHTML={{ __html: `
        .custom-scrollbar::-webkit-scrollbar {
          width: 6px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: #e2e8f0;
          border-radius: 10px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: #cbd5e1;
        }
      `}} />
    </div>
  );
}

function DetailItem({ icon: Icon, label, value }) {
  return (
    <div className="p-4 rounded-2xl bg-light border border-bordercolor/50">
      <div className="flex items-center gap-2 mb-1.5">
        <Icon className="w-3.5 h-3.5 text-accent" />
        <span className="text-[9px] font-black text-muted uppercase tracking-widest">{label}</span>
      </div>
      <p className="text-sm font-bold text-navy truncate">{value}</p>
    </div>
  );
}
