export function sortProducts(products, order) {
  const sorted = [...products];
  if (order === 'Price ascending') sorted.sort((a, b) => (a.price ?? Infinity) - (b.price ?? Infinity));
  if (order === 'Price descending') sorted.sort((a, b) => (b.price ?? -Infinity) - (a.price ?? -Infinity));
  if (order === 'Name') sorted.sort((a, b) => a.product_name.localeCompare(b.product_name));
  return sorted;
}
export async function shareProduct(product, url = window.location.href) {
  if (navigator.share) {
    try { await navigator.share({ title: product.product_name, url }); return 'Shared'; }
    catch (error) { if (error.name === 'AbortError') return ''; }
  }
  if (!navigator.clipboard?.writeText) throw new Error('Sharing unavailable. Copy the page URL from your address bar.');
  try { await navigator.clipboard.writeText(url); return 'Link copied'; }
  catch { throw new Error('Could not share this product. Copy the page URL from your address bar.'); }
}
