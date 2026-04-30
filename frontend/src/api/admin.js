/**
 * frontend/src/api/admin.js
 * API calls for scraper management and analytics.
 */

const API_BASE = "http://localhost:8000/admin";

export async function getScraperStats() {
  const resp = await fetch(`${API_BASE}/stats`);
  if (!resp.ok) throw new Error("Failed to fetch scraper stats");
  return resp.json();
}

export async function getScraperJobs(limit = 20) {
  const resp = await fetch(`${API_BASE}/scrape/status?limit=${limit}`);
  if (!resp.ok) throw new Error("Failed to fetch scraper jobs");
  return resp.json();
}

export async function getDeadLetters(limit = 50) {
  const resp = await fetch(`${API_BASE}/dead-letters?limit=${limit}`);
  if (!resp.ok) throw new Error("Failed to fetch dead letter logs");
  return resp.json();
}

export async function triggerScrape(site, category = null, gender = null) {
  const params = new URLSearchParams({ site });
  if (category) params.append("category", category);
  if (gender) params.append("gender", gender);

  const resp = await fetch(`${API_BASE}/scrape/trigger?${params.toString()}`, {
    method: "POST",
  });
  if (!resp.ok) throw new Error(`Failed to trigger scrape for ${site}`);
  return resp.json();
}

export async function getSites() {
  const resp = await fetch(`${API_BASE}/sites`);
  if (!resp.ok) throw new Error("Failed to fetch target sites");
  return resp.json();
}

export async function addSite(site) {
  const resp = await fetch(`${API_BASE}/sites`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(site),
  });
  if (!resp.ok) throw new Error("Failed to add new site");
  return resp.json();
}
export async function startCrawl(siteId) {
  const resp = await fetch(`${API_BASE}/sites/${siteId}/start`, { method: "POST" });
  if (!resp.ok) throw new Error("Failed to start crawl");
  return resp.json();
}

export async function pauseCrawl(siteId) {
  const resp = await fetch(`${API_BASE}/sites/${siteId}/pause`, { method: "POST" });
  if (!resp.ok) throw new Error("Failed to pause crawl");
  return resp.json();
}

export async function resumeCrawl(siteId) {
  const resp = await fetch(`${API_BASE}/sites/${siteId}/resume`, { method: "POST" });
  if (!resp.ok) throw new Error("Failed to resume crawl");
  return resp.json();
}

export async function stopCrawl(siteId) {
  const resp = await fetch(`${API_BASE}/sites/${siteId}/stop`, { method: "POST" });
  if (!resp.ok) throw new Error("Failed to stop crawl");
  return resp.json();
}

export async function deleteSite(siteId) {
  const resp = await fetch(`${API_BASE}/sites/${siteId}`, { method: "DELETE" });
  if (!resp.ok) throw new Error("Failed to delete site");
  return resp.json();
}

export async function resetAllData() {
  const resp = await fetch(`${API_BASE}/reset`, { method: "POST" });
  if (!resp.ok) throw new Error("Failed to reset data");
  return resp.json();
}
