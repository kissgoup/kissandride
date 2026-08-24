#!/usr/bin/env python3
#encoding=utf-8
# 驗證調優: 登出狀態(立即購買按鈕 disabled)下, ticketplus_date_auto_select
# 應偵測到「目標按鈕 disabled」並觸發頁面刷新, 且回傳 False。
import argparse
import sys
import time

import chrome_tixcraft as bot

ACTIVITY_URL = "https://ticketplus.com.tw/activity/1002c50b452980d396dfc61c6313da39"


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


driver = None
try:
    args = build_args()
    config_dict = bot.get_config_dict(args)
    if config_dict is None:
        print("Load config error!")
        sys.exit(1)

    print("launch browser (fresh profile, logged out) ...")
    driver = bot.get_driver_by_config(config_dict)
    if driver is None:
        print("driver fail!")
        sys.exit(1)

    print("goto:", ACTIVITY_URL)
    driver.get(ACTIVITY_URL)
    time.sleep(14)

    print("url:", driver.current_url)

    # sanity: button should be disabled when logged out.
    try:
        btns = driver.find_elements(bot.By.CSS_SELECTOR, 'button.nextBtn')
        for b in btns:
            print("nextBtn enabled (logged out):", b.is_enabled())
    except Exception as exc:
        print("button check fail:", exc)

    # inject JS marker; a reload will clear it.
    driver.execute_script("window.__probe_marker = 123;")

    print("=== call ticketplus_date_auto_select (expect reload) ===")
    ret = bot.ticketplus_date_auto_select(driver, config_dict)
    print("return:", ret)

    marker = driver.execute_script("return window.__probe_marker || null;")
    print("js marker after call:", marker, "(null => page was reloaded)")

    print("url after:", driver.current_url)
    print("==== verify done ====")
finally:
    if not driver is None:
        try:
            driver.quit()
        except Exception:
            pass
