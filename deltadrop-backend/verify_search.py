import asyncio
import logging
import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath("."))

from app.scrapers.universal import universal_scraper

async def main():
    logging.basicConfig(level=logging.INFO)
    query = "Sony XM5"
    print(f"--- Searching for: {query} ---")
    try:
        results = await universal_scraper.search_by_name(query)
        print(f"--- Found {len(results.get('results', []))} results ---")
        for r in results.get('results', [])[:5]:
            print(f"[{r.retailer}] {r.product_name} - ₹{r.current_price}")
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
