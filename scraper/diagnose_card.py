"""
Diagnostic: Print the inner HTML of the first div.group product card
on the /shop page to see the exact DOM structure for field selectors.
"""
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()

        print("Navigating to shop page...")
        await page.goto("https://www.kandyselection.lk/shop", wait_until="networkidle", timeout=30000)

        # Wait for products
        try:
            await page.wait_for_selector("div.group", timeout=25000)
            print("Cards found!")
        except Exception as e:
            print(f"Timeout: {e}")

        cards = await page.query_selector_all("div.group")
        print(f"Total div.group elements found: {len(cards)}")

        if cards:
            # Print the inner HTML of the first card
            first_card = cards[0]
            html = await first_card.inner_html()
            print("\n--- FIRST CARD INNER HTML ---")
            print(html[:3000])  # Print up to 3000 chars
            print("--- END CARD HTML ---")

            # Try common selectors
            for sel in ["h3", "h2", "p", "span", "div[class*='price']", "div[class*='name']", "a"]:
                els = await first_card.query_selector_all(sel)
                texts = []
                for el in els[:3]:
                    t = (await el.inner_text()).strip()
                    if t:
                        texts.append(repr(t[:60]))
                if texts:
                    print(f"  [{sel}]: {', '.join(texts)}")

        await browser.close()

asyncio.run(main())
