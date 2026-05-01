/**
 * src/api/search.js
 * API call helpers for the FiFy search backend.
 */

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

/**
 * Search by uploaded image file.
 * @param {File} file
 * @param {Object} filters - { category, gender, min_price, max_price }
 */
export async function searchByImage(file, filters = {}) {
  const form = new FormData();
  form.append("file", file);
  Object.entries(filters).forEach(([k, v]) => v != null && form.append(k, v));

  const res = await fetch(`${API_BASE}/search/image`, { method: "POST", body: form });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Search failed (${res.status})`);
  }
  return res.json();
}

/**
 * Search by text description.
 * @param {string} query
 * @param {Object} filters
 */
export async function searchByText(query, filters = {}) {
  const form = new FormData();
  form.append("query", query);
  Object.entries(filters).forEach(([k, v]) => v != null && form.append(k, v));

  const res = await fetch(`${API_BASE}/search/text`, { method: "POST", body: form });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Search failed (${res.status})`);
  }
  return res.json();
}
/**
 * Fetch a single product by ID.
 * @param {string} id
 */
export async function getProductById(id) {
  const res = await fetch(`${API_BASE}/products/${id}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch product ${id}`);
  }
  return res.json();
}
/**
 * Fetch a list of products for the home page.
 */
export async function getAllProducts(limit = 20, filters = {}, query = "") {
  const params = new URLSearchParams({ limit });
  if (filters.category) params.append("category", filters.category);
  if (filters.gender) params.append("gender", filters.gender);
  if (query) params.append("q", query);

  const res = await fetch(`${API_BASE}/products?${params.toString()}`);
  if (!res.ok) throw new Error("Failed to fetch products");
  return res.json();
}

/**
 * Return a proxied image URL to avoid hotlinking.
 */
export function getProxyImageUrl(originalUrl) {
  if (!originalUrl) return "";
  return `${API_BASE}/products/proxy-image?url=${encodeURIComponent(originalUrl)}`;
}
