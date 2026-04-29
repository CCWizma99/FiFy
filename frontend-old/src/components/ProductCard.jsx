import { useState } from "react";

const SITE_COLORS = {
  "asos.com":    "bg-black text-white",
  "zara.com":    "bg-zinc-800 text-white",
  "hm.com":      "bg-red-600 text-white",
  "uniqlo.com":  "bg-red-500 text-white",
  "zalando.com": "bg-orange-500 text-white",
};

/**
 * ProductCard — displays a single product result.
 */
export default function ProductCard({ product }) {
  const [imgError, setImgError] = useState(false);
  const badgeClass = SITE_COLORS[product.source_site] || "bg-zinc-700 text-white";

  return (
    <article
      className="glass rounded-2xl overflow-hidden flex flex-col group
                 transition-all duration-300 hover:scale-[1.02] hover:shadow-xl
                 hover:shadow-brand-500/10 hover:border-white/20 animate-slide-up"
    >
      {/* Product image */}
      <a href={product.product_url} target="_blank" rel="noopener noreferrer"
         className="block aspect-[3/4] overflow-hidden bg-zinc-900">
        {!imgError ? (
          <img
            src={product.image_url}
            alt={product.product_name}
            onError={() => setImgError(true)}
            className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-zinc-600">
            <svg className="w-10 h-10" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1}
                d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M3 21h18M3.75 3.75h16.5a.75.75 0 01.75.75v13.5a.75.75 0 01-.75.75H3.75a.75.75 0 01-.75-.75V4.5a.75.75 0 01.75-.75z" />
            </svg>
          </div>
        )}
      </a>

      {/* Card body */}
      <div className="p-4 flex flex-col gap-2 flex-1">
        {/* Source badge */}
        <span className={`self-start text-[10px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-full ${badgeClass}`}>
          {product.source_site.replace(".com", "")}
        </span>

        {/* Name */}
        <h3 className="text-sm font-medium text-zinc-100 line-clamp-2 leading-snug">
          {product.product_name}
        </h3>

        {/* Brand */}
        {product.brand && (
          <p className="text-xs text-zinc-400">{product.brand}</p>
        )}

        {/* Footer: price + link */}
        <div className="flex items-center justify-between mt-auto pt-2">
          {product.price != null ? (
            <span className="text-base font-semibold text-brand-400">
              {product.currency === "USD" ? "$" : product.currency + " "}
              {product.price.toFixed(2)}
            </span>
          ) : (
            <span className="text-xs text-zinc-500">Price unavailable</span>
          )}

          <a
            href={product.product_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs font-semibold text-brand-400 hover:text-brand-300
                       flex items-center gap-1 transition-colors"
          >
            View
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5}
                d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25" />
            </svg>
          </a>
        </div>
      </div>
    </article>
  );
}
