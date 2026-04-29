"""
Quick diagnostic: Navigate to /shop, wait for products to hydrate, then print the HTML size
and the first few product card elements found.
"""
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()

        print("Navigating to shop page...")
        await page.goto("https://www.kandyselection.lk/shop", wait_until="networkidle", timeout=30000)
        
        print("Waiting for product links to hydrate...")
        try:
            await page.wait_for_selector("a[href*='/product/']", timeout=15000)
            print("✅ Product links found!")
        except Exception as e:
            print(f"❌ Timeout waiting for product links: {e}")

        html = await page.content()
        print(f"HTML size after hydration wait: {len(html)} chars")

        # Count how many product links exist
        links = await page.query_selector_all("a[href*='/product/']")
        print(f"Product links found: {len(links)}")
        for i, link in enumerate(links[:3]):
            href = await link.get_attribute("href")
            print(f"  [{i}] {href}")

        # Try the .group selector
        groups = await page.query_selector_all(".group")
        print(f".group elements found: {len(groups)}")

        await browser.close()

asyncio.run(main())
