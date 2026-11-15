import { Link } from 'react-router-dom';
import { useFavorites } from '../state/favorites';
import FavoriteButton from '../components/FavoriteButton';
import ProductImage from '../components/ProductImage';
export default function Saved() {
  const { favorites } = useFavorites();
  return <main className="p-8"><h1 className="text-3xl">Saved items</h1>
    <p>Saved in this browser. If storage is unavailable, items remain saved for this session.</p>
    {!favorites.length && <p>No saved items yet.</p>}
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">{favorites.map(product => <article key={product.id}>
      <Link aria-label={product.product_name} to={`/product/${product.id}`}><ProductImage product={product} className="h-48" />{product.product_name}</Link>
      <FavoriteButton product={product} />
    </article>)}</div></main>;
}
