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

export async function triggerScrape(site) {
  const resp = await fetch(`${API_BASE}/scrape/trigger?site=${encodeURIComponent(site)}`, {
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
