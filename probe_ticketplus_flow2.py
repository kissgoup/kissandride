#!/usr/bin/env python3
#encoding=utf-8
"""ticketplus 探針 #2:
A. 活動頁 ticketplus_date_auto_select 連續觀察（verbose，找 0 列 bug）
B. /order/ 頁展開一個內層票區面板，看展開後的內容（票種列/qty）
C. 用 Python requests + driver cookies 回放 apis.ticketplus.com.tw API
不做最後送出。
"""
import json
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

import requests


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


def js_click(driver, el):
    driver.execute_script("arguments[0].click();", el)


def replay_api_cookies(driver, urls):
    cookies = {c["name"]: c["value"] for c in driver.get_cookies()}
    s = requests.Session()
    for k, v in cookies.items():
        s.cookies.set(k, v, domain="ticketplus.com.tw")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://ticketplus.com.tw/",
        "Origin": "https://ticketplus.com.tw",
    }
    for i, u in enumerate(urls[:8], 1):
        try:
            r = s.get(u, headers=headers, timeout=10)
            body = r.text
        except Exception as exc:
            body = "REQUEST_ERROR: %s" % exc
        name = "tp2_api_%02d.json" % i
        save(name, body)
        print("   <-", r.status_code if not body.startswith("REQUEST_ERROR") else "ERR", u[:130])


driver = None
try:
    args = build_args()
    args.homepage = ROOT_URL
    config_dict = bot.get_config_dict(args)
    config_dict["advanced"]["verbose"] = True
    config_dict["date_auto_select"]["enable"] = False  # A 階段先手動觀察，不要讓 bot 自己跳走

    print("launch browser ...")
    driver = bot.get_driver_by_config(config_dict)
    time.sleep(4)

    print("=== stage A: sign-in ===")
    if ROOT_URL not in driver.current_url:
        driver.get(ROOT_URL)
        time.sleep(4)
    bot.ticketplus_main(driver, driver.current_url, config_dict, None, None)
    time.sleep(8)

    print("=== stage A2: activity page, row-count watch ===")
    driver.get(ACTIVITY_URL)
    time.sleep(10)
    for i in range(4):
        try:
            n = len(driver.find_elements(By.CSS_SELECTOR, 'div#buyTicket > div.sesstion-item > div.row'))
            n2 = len(driver.find_elements(By.CSS_SELECTOR, 'div.sesstion-item'))
        except Exception as exc:
            n, n2 = "fail", "fail"
        print("watch[%d]: rows=%s sesstion-items=%s url_ok=%s" % (
            i, n, n2, ACTIVITY_URL in driver.current_url))
        time.sleep(1.5)

    print("=== stage A3: call bot date_auto_select (verbose) ===")
    config_dict["date_auto_select"]["enable"] = True
    is_clicked = bot.ticketplus_date_auto_select(driver, config_dict)
    print("date_auto_select ->", is_clicked)

    if not is_clicked:
        print("fallback: click first enabled nextBtn")
        for b in driver.find_elements(By.CSS_SELECTOR, 'button.nextBtn'):
            if b.is_enabled():
                try:
                    b.click()
                except Exception:
                    js_click(driver, b)
                break
        time.sleep(2)

    deadline = time.time() + 40
    while time.time() < deadline:
        time.sleep(1)
        if '/order/' in driver.current_url:
            break
    print("url now:", driver.current_url)
    if '/order/' not in driver.current_url:
        print("!!! did not reach /order/, abort recon B")
        sys.exit(0)

    time.sleep(8)
    print("=== stage B: expand one inner area panel ===")
    print("style1 nextBtn:", len(driver.find_elements(By.CSS_SELECTOR,
        "div.order-footer > div.container > div.row > div > div.row > div > button.nextBtn")))
    panels = driver.find_elements(By.CSS_SELECTOR, 'div.seats-area > div.v-expansion-panel[aria-expanded="false"]')
    print("collapsed inner panels:", len(panels))
    target = None
    for p in panels:
        try:
            t = p.text.replace("\n", " ")
        except Exception:
            continue
        print("  panel:", t[:60])
        if "剩餘" in t and "剩餘 0" not in t:
            if target is None:
                target = p
    if target is None:
        print("no available panel to expand!")
        sys.exit(0)

    print("expanding:", target.text.replace("\n", " ")[:60])
    try:
        target.click()
    except Exception:
        js_click(driver, target)
    time.sleep(3)

    # 展開後的 bot selectors 檢查
    tt_style1 = len(driver.find_elements(By.CSS_SELECTOR,
        "div.seats-area > div.v-expansion-panel > div.v-expansion-panel-content > div.v-expansion-panel-content__wrap > div.text-title"))
    tt_style2 = len(driver.find_elements(By.CSS_SELECTOR, "div.rwd-margin > div.text-title"))
    print("after expand: style1 text-title =", tt_style1, ", style2 text-title =", tt_style2)
    print("aria-expanded true inner panels:", len(driver.find_elements(By.CSS_SELECTOR,
        'div.seats-area > div.v-expansion-panel[aria-expanded="true"]')))
    print("expanded state text:", target.text.replace("\n", " | ")[:200])

    save("tp2_order_expanded.html", driver.page_source)

    # 展開面板內部結構 dump
    html = driver.page_source
    i = html.find("S1")
    start = html.rfind('<div aria-expanded="true" class="v-expansion-panel"', 0, max(i, 1))
    if start > 0:
        seg = html[start:start+5000]
        save("tp2_expanded_panel.html", seg)
        print("panel block head:", seg[:200].replace("\n", " "))

    print("=== stage C: API replay via requests+cookies ===")
    apis = []
    for kw in ["apis.ticketplus"]:
        apis += bot.get_performance_log(driver, kw)
    uniq = sorted(set(apis))
    for u in uniq:
        print("  api:", u[:150])
    replay_api_cookies(driver, uniq)

    print("==== probe2 done ====")
finally:
    if not driver is None:
        try:
            driver.quit()
        except Exception:
            pass
