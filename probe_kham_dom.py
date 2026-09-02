import asyncio
import sys

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode, BrowserConfig

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

TARGET_URL = "https://kham.com.tw/application/UTK02/UTK0201_00.aspx?PRODUCT_ID=P1D3G65D"


async def main():
    browser_cfg = BrowserConfig(headless=False)
    # 不帶 wait_for：先看實際 DOM，再決定正確 selector
    config = CrawlerRunConfig(
        remove_overlay_elements=False,
        delay_before_return_html=3.0,
        cache_mode=CacheMode.BYPASS,
    )
    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        result = await crawler.arun(url=TARGET_URL, config=config)
        print("success:", result.success)
        if result.success:
            html = result.html or ""
            print("title:", (result.metadata or {}).get("title"))
            print("html length:", len(html))
            with open("kham_page.html", "w", encoding="utf-8") as f:
                f.write(html)
            print("saved -> kham_page.html")
            print("---- head 800 ----")
            print(html[:800])
        else:
            print("fail:", result.error_message)


if __name__ == "__main__":
    asyncio.run(main())
