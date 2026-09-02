#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KHAM 售票系統爬蟲測試。

流程：
  1. 爬第 1 步：場次表 (table.eventTABLE) → 解析日期/地點/票價/可買性
     + 存 kham_step1.html / kham_step1.txt
  2. 從第一個「立即訂購」按鈕的 onclick 抽出 UTK0204_.aspx 完整網址
  3. 爬第 2 步：區域表 (table#salesTable > tbody > tr.status_tr)
     → 解析票區名稱/票價/空位張數/是否售完
     + 存 kham_step2.html / kham_step2.txt

需連外網路；kham epsf 防護會擋 headless，所以用有頭模式。
"""
import asyncio
import json
import re
import sys

from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode, BrowserConfig

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


STEP1_URL = "https://kham.com.tw/application/UTK02/UTK0201_00.aspx?PRODUCT_ID=P1D3G65D"
BASE_URL = "https://kham.com.tw/application/UTK02/"


# ========================================================================
# 第 1 步：parse 場次表 (table.eventTABLE)
# ========================================================================


def parse_step1(html: str) -> list[dict]:
    """解析 kham 場次頁 table.eventTABLE > tbody > tr。

    實際 DOM（kham_page.html 驗證）:
        <tr>
            <td>2026/10/03(六)19:30</td>
            <td><a id="PLACE_ADDRESS">...</a><span id="PLACE_NAME">臺北小巨蛋</span><br>...</td>
            <td data-th="票價(NT$)："><s><font color="lightblue">800</font></s>、3480、3880</td>
            <td><a href="javascript:;"><button class="red"
                    onclick="top.location.href='UTK0204_.aspx?PERFORMANCE_ID=...&PRODUCT_ID=...';">
                    立即訂購</button></a></td>
        </tr>
    """
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.select("table.eventTABLE > tbody > tr")
    zones: list[dict] = []
    for row in rows:
        # 只有含 <button> 的列才可買；按鈕文字需為「立即訂購」
        btn = row.find("button")
        if btn is None:
            continue
        if btn.get("disabled", None) is not None:
            continue
        btn_text = btn.get_text(" ", strip=True)
        if "立即訂購" not in btn_text:
            continue

        # 拆出 4 個 <td>（第 0 個索引是 <tr> 前綴）
        td_array = row.decode_contents().split("<td")
        def td_text(idx):
            # td_array[idx] 以「>」開頭（<td ...> 標籤的尾巴），先剝到第一個 >，
            # 再移除內部標籤
            if len(td_array) > idx:
                t = re.sub(r"^[^>]*>", "", td_array[idx])
                return re.sub(r"<[^>]+>", "", t).strip()
            return ""

        date_text = td_text(1)   # 2026/10/03(六)19:30
        venue_text = td_text(2)  # 臺北小巨蛋 ...（含 PLACE_NAME）

        # 票價欄：拆出所有價格，先偵測 <s>/lightblue（已完售）再剝除標籤
        prices: list[dict] = []
        if len(td_array) > 3:
            price_cell = td_array[3]
            # 移除 data-th 開頭屬性後，按 、 拆開
            price_cell_clean = re.sub(r'^[^>]*>', '', price_cell)
            for p in price_cell_clean.split("、"):
                # 先判已完售（保留刪除線/lightblue），再剝標籤取價格文字
                sold_out = bool(re.search(r"<s|lightblue", p))
                p_text = re.sub(r"<[^>]+>", "", p).strip()
                if not p_text:
                    continue
                # 千分位 4,680 → 4680；NT$ 前綴移除
                p_num = p_text.replace(",", "").replace("NT$", "")
                prices.append({
                    "price": p_num,
                    "sold_out": sold_out,
                })
        else:
            prices = []

        # 訂購按鈕 onclick 內含 step2 相對網址
        onclick = btn.get("onclick", "") or ""
        m = re.search(r"UTK0204_\.aspx\?[^'\"]*", onclick)
        step2_url = ""
        if m:
            step2_url = BASE_URL + m.group(0)

        zones.append({
            "date": date_text,
            "venue": venue_text,
            "prices": prices,
            "all_sold_out": bool(prices) and all(p["sold_out"] for p in prices),
            "step2_url": step2_url,
        })
    return zones


def save_step1_results(zones: list[dict]):
    lines = ["來源: %s\n" % STEP1_URL, "\n"]
    for z in zones:
        sold = "[全部已售完]" if z["all_sold_out"] else ""
        lines.append("- %s | %s %s\n" % (z["date"], z["venue"], sold))
        for p in z["prices"]:
            mark = "售完" if p["sold_out"] else "可買"
            lines.append("    NT$ %s (%s)\n" % (p["price"], mark))
        lines.append("    step2: %s\n" % z["step2_url"])
        lines.append("\n")
    with open("kham_step1.txt", "w", encoding="utf-8") as f:
        f.writelines(lines)
    print("[成功] 已將第 1 步結果儲存至 kham_step1.txt (%d 場)" % len(zones))


# ========================================================================
# 第 2 步：parse 區域表 (table#salesTable)
# ========================================================================


def parse_step2(html: str) -> list[dict]:
    """解析 kham 區域頁 table#salesTable > tbody > tr.status_tr。

    實際 DOM（kham_step2.html 驗證）:
        <tr class="status_tr" rel="a20 a21 a22" id="P1D9ZT7S" style="cursor: pointer;">
            <td><div class="colorblock" style="background-color:#DD94CD"></div></td>
            <td data-title="票區：">平面特1區4680元</td>
            <td data-title="票價：">4,680</td>
            <td data-title="空位：">4</td>
        </tr>
        <tr class="status_tr Soldout" ...>  ← 已售完
        <tr class="status_tr" rel="a53" ...><td data-title="空位：">熱賣中</td>  ← 熱賣中(不限張數)
    """
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.select("table#salesTable > tbody > tr.status_tr")
    zones: list[dict] = []
    for tr in rows:
        tds = tr.find_all("td")
        if len(tds) < 4:
            continue
        area_name = tds[1].get_text(" ", strip=True)
        ticket_price = tds[2].get_text(" ", strip=True).replace(",", "")
        remaining_text = tds[3].get_text(" ", strip=True)

        remaining = None
        sold_out = False
        if "已售完" in remaining_text:
            sold_out = True
            remaining = 0
        elif "熱賣中" in remaining_text:
            remaining = None  # 熱賣中視為不限制張數
        elif remaining_text.isdigit():
            remaining = int(remaining_text)

        zones.append({
            "row_id": tr.get("id", ""),            # P1DA05H0 ...
            "area_ids": tr.get("rel", "").split(),  # ['a20','a21','a22'] ...
            "area_name": area_name,
            "ticket_price": ticket_price,
            "remaining": remaining,
            "sold_out": sold_out,
        })
    return zones


def save_step2_results(zones: list[dict]):
    lines = ["來源: https://kham.com.tw/application/UTK02/UTK0204_.aspx\n", "\n"]
    avail = 0
    total_avail = 0
    for z in zones:
        if z["sold_out"]:
            status = "已售完"
        elif z["remaining"] is None:
            status = "熱賣中"
            avail += 1
        else:
            status = "剩 %d" % z["remaining"]
            if z["remaining"] > 0:
                avail += 1
                total_avail += z["remaining"]
        lines.append("- %-20s NT$%-6s %s  (row_id=%s rel=%s)\n" % (
            z["area_name"], z["ticket_price"], status, z["row_id"], ",".join(z["area_ids"])))
    lines.append("\n[統計] %d 區, 可用 %d 區, 空位總計 %d\n" % (len(zones), avail, total_avail))
    with open("kham_step2.txt", "w", encoding="utf-8") as f:
        f.writelines(lines)
    print("[成功] 已將第 2 步結果儲存至 kham_step2.txt (%d 區, 可用 %d 區)" % (len(zones), avail))


# ========================================================================
# 爬蟲共用
# ========================================================================


async def fetch_with_crawl4ai(url: str, filename: str, wait_selector: str | None) -> str | None:
    """用 crawl4ai 抓完整 DOM；若提供了 selector 但不存在則回報失敗。"""
    config = CrawlerRunConfig(
        remove_overlay_elements=False,
        delay_before_return_html=2.0,
        cache_mode=CacheMode.BYPASS,
    )
    if wait_selector:
        config.wait_for = f"css:{wait_selector}"
        config.wait_for_timeout = 30000

    browser_cfg = BrowserConfig(headless=False)
    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        result = await crawler.arun(url=url, config=config)
        if not result.success:
            print("[警告] crawl4ai 抓取 %s 失敗: %s" % (filename, result.error_message))
            return None
        html = result.html or ""
        with open(filename, "w", encoding="utf-8") as f:
            f.write(html)
        print("[成功] 已將完整 DOM 儲存至 %s (%d bytes)" % (filename, len(html)))
        return html


# ========================================================================
# 主流程
# ========================================================================


async def main():
    # Phase 1: 爬第 1 步場次表
    print("=" * 60)
    print("=== Phase 1: 爬第 1 步場次表 ===")
    html1 = await fetch_with_crawl4ai(STEP1_URL, "kham_step1.html", "table.eventTABLE")
    if html1 is None:
        print("[失敗] 無法取得 kham_step1.html，跳過後續步驟")
        return

    zones1 = parse_step1(html1)
    save_step1_results(zones1)
    if not zones1:
        print("[警告] 解析不到任何可買場次")
        return

    print("\n前 3 場:")
    for z in zones1[:3]:
        print(" ", z)

    # 找第一個有 step2_url 的場次
    target = next((z for z in zones1 if z["step2_url"]), None)
    if target is None:
        print("[警告] 沒有場次帶有 UTK0204_ 訂購網址")
        return

    print("\n選擇場次: %s" % target["date"])
    print("step2 URL: %s" % target["step2_url"])

    # Phase 2: 爬第 2 步區域表
    print("=" * 60)
    print("=== Phase 2: 爬第 2 步區域表 ===")
    html2 = await fetch_with_crawl4ai(target["step2_url"], "kham_step2.html", "table#salesTable")
    if html2 is None:
        print("[失敗] 無法取得 kham_step2.html")
        return

    zones2 = parse_step2(html2)
    save_step2_results(zones2)

    print("\n前 5 區:")
    for z in zones2[:5]:
        print(" ", z)


if __name__ == "__main__":
    asyncio.run(main())
