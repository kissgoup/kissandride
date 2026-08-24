#!/usr/bin/env python3
#encoding=utf-8
# 登入版唯讀探針: 模擬 -> 首頁登入 -> 活動頁, 觀察登入狀態下場次區的 DOM。
# 不做任何點擊/購買動作。
import argparse
import sys
import time

import chrome_tixcraft as bot
from selenium.webdriver.common.by import By

ROOT_URL = "https://ticketplus.com.tw/"
ACTIVITY_URL = "https://ticketplus.com.tw/activity/1002c50b452980d396dfc61c6313da39"
WAIT_SECONDS = 15


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


def dump_state(driver, label):
    print("---- [%s] ----" % label)
    try:
        print("url:", driver.current_url)
    except Exception as exc:
        print("url fail:", exc)
    for css in ['#buyTicket', 'div.sesstion-item', 'div.sesstion-item > div.row',
                'div.sesstion-item > div.row > div > div > button.nextBtn',
                'div.sesstion-item > div.row button.nextBtn', 'button.nextBtn',
                '.v-progress-circular']:
        try:
            els = driver.find_elements(By.CSS_SELECTOR, css)
            print(css, "->", len(els))
        except Exception as exc:
            print(css, "-> fail", exc)

    # button states
    try:
        btns = driver.find_elements(By.CSS_SELECTOR, 'button.nextBtn')
        for b in btns:
            try:
                print("nextBtn text:", repr(b.text), "enabled:", b.is_enabled())
            except Exception as exc:
                print("nextBtn state fail:", exc)
    except Exception as exc:
        print("nextBtn find fail:", exc)

    # 尚未開賣 / 銷售 markers anywhere
    try:
        body_text = driver.find_element(By.TAG_NAME, 'body').text
        for marker in ["尚未開賣", "銷售一空", "已售完", "已售罄", "立即購買", "開放購票", "倒數"]:
            if marker in body_text:
                print("body marker:", marker)
    except Exception as exc:
        print("body text fail:", exc)


driver = None
try:
    args = build_args()
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
    url = ""
    try:
        url = driver.current_url
    except Exception:
        pass
    print("initial url:", url)

    if url.lower() != ROOT_URL:
        print("goto root:", ROOT_URL)
        driver.get(ROOT_URL)
        time.sleep(4)
        url = driver.current_url

    print("=== sign-in ===")
    bot.ticketplus_main(driver, url, config_dict, None, None)
    time.sleep(8)
    try:
        all_cookies = bot.list_all_cookies(driver)
        print("signed-in:", 'user' in all_cookies)
    except Exception as exc:
        print("cookie check fail:", exc)

    print("=== goto activity (logged-in) ===")
    driver.get(ACTIVITY_URL)
    time.sleep(WAIT_SECONDS)
    dump_state(driver, "activity logged-in, after %ss" % WAIT_SECONDS)

    # extra: wait a bit more to catch delayed render
    time.sleep(10)
    dump_state(driver, "activity logged-in, after +10s")

    print("==== probe done ====")
finally:
    if not driver is None:
        try:
            driver.quit()
        except Exception:
            pass
