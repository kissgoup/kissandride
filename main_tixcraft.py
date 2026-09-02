import asyncio
import re
import sys

from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode, BrowserConfig

# 避免 Windows 主控台以 GBK/cp950 印中文時變亂碼
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

TARGET_URL = "https://tixcraft.com/ticket/area/26_5sos/23045"
AREA_LIST_SELECTOR = "div.area-list"


async def main():
    # 關鍵修正：tixcraft 的 epsf 防護會偵測 headless 瀏覽器並回傳
    # "Let's Get Your Identity Verified" 驗證頁（根本沒有售票資料）。
    # 必須用有頭瀏覽器（headless=False）才能取得真正的售票頁。
    browser_cfg = BrowserConfig(headless=False)

    config = CrawlerRunConfig(
        # 停用遮罩清理，確保 script 與 style 完好保留
        remove_overlay_elements=False,
        # 頁面載入後強制等待，確保拓元的動態 JS 載入完畢
        delay_before_return_html=2.0,
        # 繞過快取
        cache_mode=CacheMode.BYPASS,
        # 等到真正的區域清單出現；若卡在驗證頁會等到逾時並回報失敗
        wait_for=f"css:{AREA_LIST_SELECTOR}",
        wait_for_timeout=60000,
    )

    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        result = await crawler.arun(url=TARGET_URL, config=config)

        if not result.success:
            print(f"抓取失敗: {result.error_message}")
            return

        html = result.html or ""

        # 存成 HTML 檔案（即使是驗證頁也存下來，方便除錯）
        with open("tixcraft_page.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("[成功] 已將完整 DOM 結構儲存至 tixcraft_page.html")

        # 解析區域資料（以是否解析到資料判斷是否仍被防護攔截）
        zones = parse_areas(html)
        if not zones:
            print("警告: 解析不到任何區域資料，可能仍被防護攔截（可檢查 tixcraft_page.html）")
            return
        print(f"\n=== 區域資料 (共 {len(zones)} 區) ===")
        for z in zones:
            print(z)

        # 存成純文字檔（避免主控台編碼問題）
        with open("tixcraft_areas.txt", "w", encoding="utf-8") as f:
            f.write(f"來源: {TARGET_URL}\n")
            for z in zones:
                f.write(str(z) + "\n")
        print("\n[成功] 已將解析結果儲存至 tixcraft_areas.txt")


def parse_areas(html: str) -> list[dict]:
    """解析 tixcraft /ticket/area/ 頁面的區域清單。

    DOM 結構（每個群組）:
        <div class="zone area-list">
            <div class="zone-label" data-id="group_0"> <b>群組名稱</b> </div>
            <ul id="group_0" class="area-list">
                <li class="select_form_a"><a id="23045_46">區域名稱 <font color="#FF0000">剩餘 35</font></a></li>
                <li><font color="#AAAAAA">區域名稱 已售完</font></li>
            </ul>
        </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    container = soup.select_one("div.zone.area-list")
    if container is None:
        return []

    zones: list[dict] = []
    for label in container.select("div.zone-label"):
        group_name = label.get_text(" ", strip=True)
        ul = label.find_next_sibling("ul", class_="area-list")
        if ul is None:
            continue
        for li in ul.select("li"):
            a = li.select_one("a[id]")
            item = {
                "group": group_name,
                "area": "",
                "area_id": "",
                "status": "",
                "remaining": None,
            }
            if a is not None:
                area_id = a.get("id", "")
                item["area_id"] = area_id
                item["area"] = a.get_text(" ", strip=True)
                font = a.select_one("font")
                if font is not None:
                    marker = font.get_text(" ", strip=True)
                    item["area"] = item["area"].replace(marker, "").strip()
                    # 紅字標記：#FF0000，內容可能是「剩餘 N」「熱賣中」「售罄」等
                    m = re.search(r"剩餘\s*(\d+)", marker)
                    if m:
                        item["status"] = "available"
                        item["remaining"] = int(m.group(1))
                    elif any(k in marker for k in ("售罄", "完售", "售完")):
                        item["status"] = "sold_out"
                        item["remaining"] = 0
                    elif marker in ("熱賣中", "販售中", "開放中"):
                        item["status"] = "available"
                        item["remaining"] = None
                    else:
                        item["status"] = "available"
                else:
                    item["status"] = "available"
            else:
                # 沒有 <a> 連結：灰色已售完
                item["area"] = li.get_text(" ", strip=True).replace("已售完", "").strip()
                item["status"] = "sold_out"
                item["remaining"] = 0
            zones.append(item)
    return zones


if __name__ == "__main__":
    asyncio.run(main())
