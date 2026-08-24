#!/usr/bin/env python3
#encoding=utf-8
# 唯讀探針: 載入 ticketplus 活動頁, 傾印場次區的 DOM 結構。
# 不做任何點擊/購買動作, 只觀察頁面結構。
import argparse
import sys
import time

import chrome_tixcraft as bot
from selenium.webdriver.common.by import By

ACTIVITY_URL = "https://ticketplus.com.tw/activity/1002c50b452980d396dfc61c6313da39"
WAIT_SECONDS = 12


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


def safe(css):
    try:
        els = driver.find_elements(By.CSS_SELECTOR, css)
        return len(els)
    except Exception:
        return -1


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

    print("goto:", ACTIVITY_URL)
    driver.get(ACTIVITY_URL)
    time.sleep(WAIT_SECONDS)

    print("url:", driver.current_url)
    try:
        print("title:", driver.title)
    except Exception as exc:
        print("title fail:", exc)

    print("---- selector counts ----")
    print("#buyTicket:", safe('#buyTicket'))
    print("div.sesstion-item:", safe('div.sesstion-item'))
    print("div.sesstion-item > div.row:", safe('div.sesstion-item > div.row'))
    print("button[type=button]:", safe('button'))
    print("v-progress-circular:", safe('.v-progress-circular'))

    print("---- buy-area html (if #buyTicket exists) ----")
    try:
        bt = driver.find_element(By.CSS_SELECTOR, '#buyTicket')
        html = bt.get_attribute('outerHTML')
        print(html[:4000])
    except Exception as exc:
        print("#buyTicket not found:", exc)

    print("---- buttons containing 立即/尚未/銷售 ----")
    try:
        btns = driver.find_elements(By.CSS_SELECTOR, 'button')
        for b in btns:
            txt = ""
            try:
                txt = b.text.replace("\n", " ")
            except Exception:
                pass
            if any(k in txt for k in ["立即", "尚未", "銷售", "完售", "已售"]):
                print("button text:", txt, "| disabled:", end=" ")
                try:
                    print(b.is_enabled())
                except Exception:
                    print("?")
                # print a small ancestor chain for selector inference
                try:
                    parent = b.find_element(By.XPATH, '..')
                    print("   parent class:", parent.get_attribute('class'))
                    grand = parent.find_element(By.XPATH, '..')
                    print("   grandparent class:", grand.get_attribute('class'))
                except Exception:
                    pass
    except Exception as exc:
        print("scan buttons fail:", exc)

    print("---- body text scan (尚未開賣 / 銷售一空 markers) ----")
    try:
        body_text = driver.find_element(By.TAG_NAME, 'body').text
        for marker in ["尚未開賣", "銷售一空", "已售完", "已售罄", "開賣"]:
            if marker in body_text:
                print("body contains marker:", marker)
    except Exception as exc:
        print("body text fail:", exc)

    print("---- performance log: ticketplus api urls ----")
    url_list = bot.get_performance_log(driver, 'apis.ticketplus.com.tw')
    print("api log count:", len(url_list))
    for u in url_list[:10]:
        print("api:", u[:200])

    print("==== probe done ====")
finally:
    if not driver is None:
        try:
            driver.quit()
        except Exception:
            pass
