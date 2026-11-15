import { getProxyImageUrl } from '../api/search';
export default function ProductImage({ product, ...props }) {
  return <img {...props} src={getProxyImageUrl(product.image_url) || '/product-fallback.svg'} alt={product.product_name}
    onError={e => { if (!e.currentTarget.src.endsWith('/product-fallback.svg')) e.currentTarget.src = '/product-fallback.svg'; }} />;
}
