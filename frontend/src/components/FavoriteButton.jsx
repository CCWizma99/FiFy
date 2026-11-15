import { Heart } from 'lucide-react';
import { useFavorites } from '../state/favorites';
export default function FavoriteButton({ product }) {
  const { isSaved, toggle } = useFavorites();
  const saved = isSaved(product.id);
  return <button aria-label={`${saved ? 'Unsave' : 'Save'} ${product.product_name}`} aria-pressed={saved}
    onClick={e => { e.stopPropagation(); toggle(product); }} className="p-2 rounded-full bg-white text-navy border">
    <Heart size={18} fill={saved ? 'currentColor' : 'none'} />
  </button>;
}
