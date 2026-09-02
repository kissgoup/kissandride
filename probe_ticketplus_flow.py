#!/usr/bin/env python3
#encoding=utf-8
"""ticketplus 全流程唯讀探針: 登入 -> 活動頁 -> 場次點擊(走 bot 自己的路徑)
-> 佇列觀察 -> /order/ 頁面 DOM + API 傾印。
不做最後送出（不按 nextBtn、不填驗證碼），不會產生訂單。

輸出檔:
  tp_flow_1_activity.html   活動頁 HTML
  tp_flow_2_queue.html      佇列/劃位 spinner 頁 HTML（若有）
  tp_flow_3_order.html      order 頁 HTML
  tp_flow_apis.txt          各階段攔到的 API URL
  tp_flow_api_NNN.json      回放 GET API 的回應
"""
import argparse
import json
import os
import sys
import time

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import chrome_tixcraft as bot
from selenium.webdriver.common.by import By

ROOT_URL = "https://ticketplus.com.tw/"
ACTIVITY_URL = "https://ticketplus.com.tw/activity/0dcd13114224adf9ff51382e8b535894"
API_KEYWORDS = ["apis.ticketplus", "ticketplus.com.tw/api", "/api/"]

QUEUE_WAIT_MAX = 120          # 佇列最多觀察秒數
ORDER_SETTLE_WAIT = 8         # order 頁 Vue 完成渲染等待


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
    parser.add_argument("--browser", type=str, default='',
                        choices=['chrome', 'firefox', 'edge', 'safari', 'brave'])
    parser.add_argument("--window_size", type=str, default=None)
    parser.add_argument("--proxy_server", type=str, default=None)
    return parser.parse_args()


def save(name, content):
    with open(name, "w", encoding="utf-8") as f:
        f.write(content)
    print("saved:", name, len(content), "bytes")


def drain_api_urls(driver, label, collected):
    """撈 performance log，把 ticketplus API URL 依階段收集。"""
    urls = []
    for kw in API_KEYWORDS:
        urls += bot.get_performance_log(driver, kw)
    uniq = sorted(set(urls))
    print("---- API [%s]: %d ----" % (label, len(uniq)))
    for u in uniq:
        print("  ", u[:160])
    collected[label] = uniq
    return uniq


def count(driver, css):
    try:
        return len(driver.find_elements(By.CSS_SELECTOR, css))
    except Exception as exc:
        return "fail:%s" % exc


def dump_activity(driver):
    print("---- activity DOM ----")
    print("url:", driver.current_url)
    for css in ['#buyTicket', 'div.sesstion-item', 'div.sesstion-item > div.row',
                'div.sesstion-item > div.row button.nextBtn', 'button.nextBtn',
                '.v-progress-circular']:
        print(" ", css, "->", count(driver, css))
    try:
        rows = driver.find_elements(By.CSS_SELECTOR, 'div#buyTicket > div.sesstion-item > div.row')
        for i, r in enumerate(rows):
            try:
                txt = " | ".join(r.text.split("\n"))
                print("  row[%d] %s" % (i, txt[:150]))
            except Exception:
                pass
        btns = driver.find_elements(By.CSS_SELECTOR, 'div.sesstion-item button.nextBtn')
        for i, b in enumerate(btns):
            print("  btn[%d] text=%r enabled=%s class=%s" % (i, b.text, b.is_enabled(), b.get_attribute("class")))
    except Exception as exc:
        print("  rows fail:", exc)


def dump_order(driver):
    print("---- order DOM ----")
    print("url:", driver.current_url)
    css_list = [
        "div.order-footer > div.container > div.row > div > button.nextBtn",
        "div.order-footer > div.container > div.row > div > div.row > div > button.nextBtn",
        "div.rwd-margin > div.text-title",
        "div.seats-area > div.v-expansion-panel",
        "div.v-expansion-panel[aria-expanded='false']",
        "div.price-group > div",
        "input[placeholder='請輸入驗證碼']",
        "img[alt='驗證碼']",
        "input[type='checkbox']",
    ]
    for css in css_list:
        print(" ", css, "->", count(driver, css))

    # 票區標題（style2）
    try:
        titles = driver.find_elements(By.CSS_SELECTOR, "div.rwd-margin > div.text-title")
        for i, t in enumerate(titles):
            print("  text-title[%d] %s" % (i, " | ".join(t.text.split("\n"))[:140]))
    except Exception as exc:
        print("  text-title fail:", exc)

    # 展開面板（style1）
    try:
        panels = driver.find_elements(By.CSS_SELECTOR, "div.seats-area > div.v-expansion-panel")
        for i, p in enumerate(panels):
            try:
                print("  panel[%d] aria-expanded=%s text=%s" % (
                    i, p.get_attribute("aria-expanded"),
                    " | ".join(p.text.split("\n"))[:160]))
            except Exception:
                pass
    except Exception as exc:
        print("  panels fail:", exc)

    # 訂單頁可見文字重點
    try:
        body_text = driver.find_element(By.TAG_NAME, "body").text
        for marker in ["排隊", "劃位", "請稍候", "驗證碼", "同意", "加購", "下一步", "剩餘", "票種"]:
            if marker in body_text:
                print("  body marker:", marker)
    except Exception as exc:
        print("  body text fail:", exc)


def replay_apis(driver, urls, out_prefix="tp_flow_api_"):
    """same-origin GET 回放，存 JSON body。"""
    idx = 0
    for u in urls:
        if idx >= 15:
            print("  replay limit reached")
            break
        if not u.startswith("http"):
            continue
        js = """
        var done = arguments[1];
        fetch(arguments[0], {credentials:'include', headers:{'accept':'application/json'}})
          .then(function(r){ return r.text(); })
          .then(function(t){ done(t); })
          .catch(function(e){ done('FETCH_ERROR: '+e); });
        """
        try:
            driver.set_script_timeout(15)
            body = driver.execute_async_script(js, u)
        except Exception as exc:
            print("  replay fail:", u[:100], exc)
            continue
        idx += 1
        name = "%s%03d.json" % (out_prefix, idx)
        save(name, body or "")
        print("   <-", u[:120])


driver = None
collected = {}
try:
    args = build_args()
    args.homepage = ROOT_URL  # 這支探針固定從 ticketplus 首頁開始
    config_dict = bot.get_config_dict(args)
    if config_dict is None:
        print("Load config error!")
        sys.exit(1)

    print("launch browser ...")
    driver = bot.get_driver_by_config(config_dict)
    if driver is None:
        print("driver fail!")
        sys.exit(1)

    time.sleep(4)
    print("=== stage A: sign-in ===")
    url = driver.current_url
    print("initial url:", url)
    if ROOT_URL not in url:
        driver.get(ROOT_URL)
        time.sleep(4)
    bot.ticketplus_main(driver, driver.current_url, config_dict, None, None)
    time.sleep(8)
    try:
        all_cookies = bot.list_all_cookies(driver)
        print("signed-in:", 'user' in all_cookies)
    except Exception as exc:
        print("cookie check fail:", exc)

    print("=== stage B: activity page ===")
    driver.get(ACTIVITY_URL)
    time.sleep(12)
    dump_activity(driver)
    try:
        save("tp_flow_1_activity.html", driver.page_source)
    except Exception as exc:
        print("save activity html fail:", exc)
    drain_api_urls(driver, "activity", collected)

    print("=== stage C: click session via bot path ===")
    try:
        is_clicked = bot.ticketplus_date_auto_select(driver, config_dict)
        print("ticketplus_date_auto_select ->", is_clicked)
    except Exception as exc:
        print("date_auto_select fail:", exc)
        is_clicked = False
    if not is_clicked:
        print("fallback: click first enabled nextBtn")
        try:
            for b in driver.find_elements(By.CSS_SELECTOR, 'button.nextBtn'):
                if b.is_enabled():
                    b.click()
                    is_clicked = True
                    break
        except Exception as exc:
            print("fallback click fail:", exc)

    # 等 /order/ 或佇列
    order_url = None
    deadline = time.time() + 40
    while time.time() < deadline:
        time.sleep(1)
        try:
            cur = driver.current_url
        except Exception:
            continue
        if '/order/' in cur:
            order_url = cur
            break
    print("after click url:", order_url or driver.current_url)

    print("=== stage D: queue watch ===")
    queue_saved = False
    deadline = time.time() + QUEUE_WAIT_MAX
    while time.time() < deadline:
        try:
            cur = driver.current_url
        except Exception:
            cur = ""
        if '/order/' not in cur:
            print("left /order/ ->", cur)
            break
        if bot.ticketplus_queue_in_progress(driver):
            if not queue_saved:
                print("[queue] spinner detected, snapshot...")
                try:
                    save("tp_flow_2_queue.html", driver.page_source)
                    queue_saved = True
                except Exception as exc:
                    print("save queue html fail:", exc)
            time.sleep(3)
            continue
        print("[queue] not in progress now.")
        break

    if '/order/' in (order_url or ""):
        print("=== stage E: order page dump ===")
        time.sleep(ORDER_SETTLE_WAIT)
        dump_order(driver)
        try:
            save("tp_flow_3_order.html", driver.page_source)
        except Exception as exc:
            print("save order html fail:", exc)
        apis = drain_api_urls(driver, "order", collected)
        replay_apis(driver, [u for u in apis if '/order' in u or 'config' in u or 'activity' in u])
    else:
        print("never reached /order/, final url:", driver.current_url)

    # 彙總 API 清單
    lines = []
    for stage, urls in collected.items():
        lines.append("==== %s ====" % stage)
        lines += urls
    save("tp_flow_apis.txt", "\n".join(lines))

    print("==== probe done ====")
finally:
    if not driver is None:
        try:
            driver.quit()
        except Exception:
            pass
