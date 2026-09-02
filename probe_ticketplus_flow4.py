#!/usr/bin/env python3
#encoding=utf-8
"""ticketplus 探針 #4: 在 /order/ 頁直接跑 bot 的 ticketplus_order_expansion_panel
(layout 1)，驗證: 展開哪個票區、qty 是否指派成功、熱賣中票區的 data-count/data-limit。
不按 nextBtn、不碰驗證碼 -> 不會送出訂單。qty 指派只影響本頁狀態，可逆。
"""
import sys
import time

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse
import chrome_tixcraft as bot
from selenium.webdriver.common.by import By

ROOT_URL = "https://ticketplus.com.tw/"
ACTIVITY_URL = "https://ticketplus.com.tw/activity/0dcd13114224adf9ff51382e8b535894"


def save(name, content):
    with open(name, "w", encoding="utf-8") as f:
        f.write(content)
    print("saved:", name, len(content), "bytes")


def build_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, default=None)
    parser.add_argument("--homepage", type=str, default=None)
    parser.add_argument("--ticket_number", type=int, default=None)
    parser.add_argument("--tixcraft_sid", type=str, default=None)
    parser.add_argument("--kktix_account", type=str, default=None)
    parser.add_argument("--kktix_password", type=str, default=None)
    parser.add_argument("--ibonqware", type=str, default=None)
    parser.add_argument("--headless", type=str, default=None)
    parser.add_argument("--browser", type=str, default='', choices=['chrome'])
    parser.add_argument("--window_size", type=str, default=None)
    parser.add_argument("--proxy_server", type=str, default=None)
    return parser.parse_args()


def count(driver, css):
    try:
        return len(driver.find_elements(By.CSS_SELECTOR, css))
    except Exception:
        return "fail"


def panel_rows(driver):
    """回傳 [(name_text, aria_expanded, panel_el)]。"""
    out = []
    for p in driver.find_elements(By.CSS_SELECTOR, 'div.seats-area > div.v-expansion-panel'):
        try:
            out.append((p.text.replace("\n", " "), p.get_attribute("aria-expanded"), p))
        except Exception:
            continue
    return out


driver = None
try:
    args = build_args()
    args.homepage = ROOT_URL
    config_dict = bot.get_config_dict(args)
    config_dict["date_auto_select"]["enable"] = False

    print("area_keyword in settings:", repr(config_dict["area_auto_select"]["area_keyword"]))
    print("area_auto_select mode:", config_dict["area_auto_select"]["mode"])
    print("ticket_number:", config_dict["ticket_number"])

    print("launch browser ...")
    driver = bot.get_driver_by_config(config_dict)
    time.sleep(4)

    print("=== sign-in ===")
    if ROOT_URL not in driver.current_url:
        driver.get(ROOT_URL)
        time.sleep(4)
    bot.ticketplus_main(driver, driver.current_url, config_dict, None, None)
    time.sleep(8)

    print("=== go activity -> order ===")
    driver.get(ACTIVITY_URL)
    time.sleep(10)
    for b in driver.find_elements(By.CSS_SELECTOR, 'button.nextBtn'):
        if b.is_enabled():
            try:
                b.click()
            except Exception:
                driver.execute_script("arguments[0].click();", b)
            break
    deadline = time.time() + 40
    while time.time() < deadline:
        time.sleep(1)
        if '/order/' in driver.current_url:
            break
    print("url:", driver.current_url)
    if '/order/' not in driver.current_url:
        print("!!! no /order/")
        sys.exit(0)
    time.sleep(8)

    print("=== nextBtn state (before) ===")
    btn = driver.find_elements(By.CSS_SELECTOR,
        "div.order-footer > div.container > div.row > div > div.row > div > button.nextBtn")
    print("style1 nextBtn count:", len(btn))
    if btn:
        print("enabled:", btn[0].is_enabled(), "text:", btn[0].text)

    print("=== expand R1 (熱賣中) and read data attrs ===")
    for name, aria, p in panel_rows(driver):
        if name.startswith("R1"):
            try:
                hdr = p.find_element(By.CSS_SELECTOR, 'button.v-expansion-panel-header')
                driver.execute_script("arguments[0].click();", hdr)
                print("expanded R1")
            except Exception as exc:
                print("R1 expand fail:", exc)
            break
    time.sleep(2)
    plus_btns = driver.find_elements(By.CSS_SELECTOR,
        'div.seats-area > div.v-expansion-panel[aria-expanded="true"] .count-button button i.mdi-plus')
    print("mdi-plus in expanded panels:", len(plus_btns))
    # 讀 plus 按鈕的 data-count / data-limit（在 button 上，不在 i 上）
    pb = driver.find_elements(By.CSS_SELECTOR,
        'div.seats-area > div.v-expansion-panel[aria-expanded="true"] .count-button button[data-count]')
    for i, b in enumerate(pb):
        print("  plus[%d] data-count=%s data-limit=%s" % (
            i, b.get_attribute("data-count"), b.get_attribute("data-limit")))
    qty_divs = driver.find_elements(By.CSS_SELECTOR,
        'div.seats-area > div.v-expansion-panel[aria-expanded="true"] div.count-button > div')
    for i, q in enumerate(qty_divs):
        print("  qty[%d] text=%r" % (i, q.text.strip()))

    print("=== run bot: ticketplus_order_expansion_panel (layout 1) ===")
    ret = bot.ticketplus_order_expansion_panel(driver, config_dict, 1, None)
    print("is_price_assign_by_bot ->", ret)
    time.sleep(2)

    print("=== panels after bot run ===")
    for name, aria, p in panel_rows(driver):
        print("  [%s] %s" % (aria, name[:60]))

    qty_divs = driver.find_elements(By.CSS_SELECTOR,
        'div.seats-area > div.v-expansion-panel[aria-expanded="true"] div.count-button > div')
    for i, q in enumerate(qty_divs):
        print("  qty after[%d] text=%r" % (i, q.text.strip()))

    print("=== nextBtn state (after) ===")
    btn = driver.find_elements(By.CSS_SELECTOR,
        "div.order-footer > div.container > div.row > div > div.row > div > button.nextBtn")
    if btn:
        print("enabled:", btn[0].is_enabled(), "text:", btn[0].text)

    save("tp4_order_after_bot.html", driver.page_source)
    print("==== probe4 done (未按 nextBtn、未碰驗證碼) ====")
finally:
    if not driver is None:
        try:
            driver.quit()
        except Exception:
            pass
