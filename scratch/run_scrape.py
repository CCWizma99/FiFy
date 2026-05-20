import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from scraper.executor import run_site

async def main():
    if len(sys.argv) < 2:
        print("Usage: python scratch/run_scrape.py <site_domain>")
        return
    site = sys.argv[1]
    await run_site(site)

if __name__ == "__main__":
    asyncio.run(main())
