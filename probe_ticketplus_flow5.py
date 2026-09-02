#!/usr/bin/env python3
#encoding=utf-8
"""探針 #5: 驗證日期列 fallback 修復 — 讓 bot 自己的 ticketplus_date_auto_select
完成場次點擊（無 fallback），確認抵達 /order/。不按下一步、不碰驗證碼。
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

ROOT_URL = "https://ticketplus.com.tw/"
ACTIVITY_URL = "https://ticketplus.com.tw/activity/0dcd13114224adf9ff51382e8b535894"


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


driver = None
try:
    args = build_args()
    args.homepage = ROOT_URL
    config_dict = bot.get_config_dict(args)
    config_dict["advanced"]["verbose"] = True
    config_dict["date_auto_select"]["enable"] = True

    driver = bot.get_driver_by_config(config_dict)
    time.sleep(4)

    if ROOT_URL not in driver.current_url:
        driver.get(ROOT_URL)
        time.sleep(4)
    bot.ticketplus_main(driver, driver.current_url, config_dict, None, None)
    time.sleep(6)

    driver.get(ACTIVITY_URL)
    time.sleep(10)

    print("=== bot date_auto_select (3 tries max) ===")
    clicked = False
    for i in range(3):
        clicked = bot.ticketplus_date_auto_select(driver, config_dict)
        print("try %d -> %s" % (i + 1, clicked))
        if clicked:
            break
        time.sleep(2)

    deadline = time.time() + 40
    while time.time() < deadline:
        time.sleep(1)
        if '/order/' in driver.current_url:
            break
    print("url now:", driver.current_url)
    ok = clicked and ('/order/' in driver.current_url)
    print("RESULT:", "PASS - bot 點擊場次並抵達 /order/" if ok else "FAIL")

    if ok:
        time.sleep(6)
        from selenium.webdriver.common.by import By
        btn = driver.find_elements(By.CSS_SELECTOR,
            "div.order-footer > div.container > div.row > div > div.row > div > button.nextBtn")
        if btn:
            print("order nextBtn enabled:", btn[0].is_enabled())
finally:
    if not driver is None:
        try:
            driver.quit()
        except Exception:
            pass
