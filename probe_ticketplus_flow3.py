#!/usr/bin/env python3
#encoding=utf-8
"""ticketplus 探針 #3:
A. 活動頁: div.sesstion-item 真實結構 dump（找 div.row 去哪了）
B. order 頁: JS click button.v-expansion-panel-header 展開 S1,
   追蹤 aria-expanded 變化與展開後內容 (text-title / count-button / mdi-plus)
不做最後送出。
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
    except Exception as exc:
        return "fail"


driver = None
try:
    args = build_args()
    args.homepage = ROOT_URL
    config_dict = bot.get_config_dict(args)
    config_dict["date_auto_select"]["enable"] = False

    print("launch browser ...")
    driver = bot.get_driver_by_config(config_dict)
    time.sleep(4)

    print("=== stage A: sign-in ===")
    if ROOT_URL not in driver.current_url:
        driver.get(ROOT_URL)
        time.sleep(4)
    bot.ticketplus_main(driver, driver.current_url, config_dict, None, None)
    time.sleep(8)

    print("=== stage A2: activity structure dump ===")
    driver.get(ACTIVITY_URL)
    time.sleep(10)
    for css in ['div#buyTicket', 'div.sesstion-item',
                'div.sesstion-item > div.row', 'div.sesstion-item div.row',
                'div.sesstion-item button.nextBtn']:
        print(" ", css, "->", count(driver, css))
    try:
        items = driver.find_elements(By.CSS_SELECTOR, 'div.sesstion-item')
        for i, it in enumerate(items[:2]):
            html = it.get_attribute("outerHTML")
            print("---- sesstion-item[%d] outerHTML (%d chars) ----" % (i, len(html)))
            print(html[:2500])
            print("---- (truncated) ----")
            if i == 0:
                save("tp3_sesstion_item0.html", html)
    except Exception as exc:
        print("dump sesstion-item fail:", exc)
    save("tp3_activity.html", driver.page_source)

    print("=== stage B: go to /order/ ===")
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
    print("url now:", driver.current_url)
    if '/order/' not in driver.current_url:
        print("!!! no /order/, abort")
        sys.exit(0)
    time.sleep(8)

    panels = driver.find_elements(By.CSS_SELECTOR, 'div.seats-area > div.v-expansion-panel')
    print("inner panels:", len(panels))
    target = None
    for p in panels:
        try:
            t = p.text.replace("\n", " ")
        except Exception:
            continue
        if "S1" in t:
            target = p
            break
    if target is None:
        print("no S1 panel")
        sys.exit(0)

    def panel_state():
        try:
            return target.get_attribute("aria-expanded")
        except Exception as exc:
            return "stale:%s" % type(exc).__name__

    print("before click aria-expanded:", panel_state())

    # 嘗試 1: JS click 在 header button 上（bot 的 find_element('button') 等價目標）
    try:
        hdr = target.find_element(By.CSS_SELECTOR, 'button.v-expansion-panel-header')
        print("header button found:", hdr.get_attribute("class"))
        driver.execute_script("arguments[0].click();", hdr)
        print("js clicked header button")
    except Exception as exc:
        print("header button click fail:", exc)

    for wait in (0.5, 2, 4):
        time.sleep(wait)
        print("  t+%ss aria-expanded:" % wait, panel_state())
        print("  style1 text-title:", count(driver,
            "div.seats-area > div.v-expansion-panel > div.v-expansion-panel-content > div.v-expansion-panel-content__wrap > div.text-title"))
        print("  count-button:", count(driver, 'div.count-button'), " mdi-plus:", count(driver, 'i.mdi-plus'))

    # 若還沒展開，嘗試 2: 原生 click 在 header button
    if panel_state() != "true":
        print("still collapsed, try native click on header button")
        try:
            hdr = target.find_element(By.CSS_SELECTOR, 'button.v-expansion-panel-header')
            hdr.click()
            print("native clicked header button")
        except Exception as exc:
            print("native click fail:", exc)
        for wait in (0.5, 2):
            time.sleep(wait)
            print("  aria-expanded:", panel_state())

    print("final aria-expanded:", panel_state())
    print("style1 text-title:", count(driver,
        "div.seats-area > div.v-expansion-panel > div.v-expansion-panel-content > div.v-expansion-panel-content__wrap > div.text-title"))
    print("count-button:", count(driver, 'div.count-button'), " mdi-plus:", count(driver, 'i.mdi-plus'))
    print("v-input (qty steppers):", count(driver, 'div.v-input'))

    if panel_state() == "true":
        save("tp3_order_expanded.html", driver.page_source)
        html = driver.page_source
        i = html.find("S1")
        start = html.rfind('<div aria-expanded="true" class="v-expansion-panel"', 0, max(i, 1))
        if start > 0:
            save("tp3_expanded_panel.html", html[start:start+6000])
            print("expanded panel block saved")
    else:
        save("tp3_order_still_collapsed.html", driver.page_source)
        print("!!! panel never expanded, saved still-collapsed html")

    print("==== probe3 done ====")
finally:
    if not driver is None:
        try:
            driver.quit()
        except Exception:
            pass
