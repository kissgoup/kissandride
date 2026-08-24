#!/usr/bin/env python3
#encoding=utf-8
# 模擬 maxbot 針對 ticketplus 活動頁的購票流程:
#   首頁登入(遠大帳密) -> 活動頁(立即購買) -> 訂購頁(選區/選張數/下一步) -> 確認頁(勾同意, 留人工)
# 直接呼叫 chrome_tixcraft.py 的既有函式, 不修改原始 bot。
import argparse
import sys
import time

import chrome_tixcraft as bot

ROOT_URL = "https://ticketplus.com.tw/"
ACTIVITY_URL = "https://ticketplus.com.tw/activity/1002c50b452980d396dfc61c6313da39"

# 抵達確認頁後, 保留瀏覽器多久(秒)供人工檢視, 之後自動關閉。
CONFIRM_HOLD_SECONDS = 60
# 整體模擬最長執行時間(秒)
MAX_RUN_SECONDS = 300


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


def main():
    args = build_args()
    config_dict = bot.get_config_dict(args)
    if config_dict is None:
        print("Load config error!")
        sys.exit(1)

    account = config_dict["advanced"]["ticketplus_account"]
    print("account:", account)
    print("homepage(config):", config_dict["homepage"])
    print("activity url:", ACTIVITY_URL)

    print("=== [1/4] launch browser (undetected_chromedriver + Maxbot extension) ===")
    driver = bot.get_driver_by_config(config_dict)
    if driver is None:
        print("web driver launch fail!")
        sys.exit(1)

    time.sleep(4)
    url = ""
    try:
        url = driver.current_url
    except Exception as exc:
        print("get current_url fail:", exc)
    print("initial url:", url)

    # uc loader 已將 homepage 導向 root(因 ticketplus_account 有值), 再確認一次。
    if url.lower() != ROOT_URL:
        print("navigate to root for sign-in:", ROOT_URL)
        try:
            driver.get(ROOT_URL)
            time.sleep(4)
        except Exception as exc:
            print(exc)
        try:
            url = driver.current_url
        except Exception:
            pass
    print("url after ensure-root:", url)

    print("=== [2/4] auto sign-in (ticketplus_main @ root) ===")
    bot.ticketplus_main(driver, url, config_dict, None, None)
    time.sleep(8)

    is_signed = False
    try:
        all_cookies = bot.list_all_cookies(driver)
        if 'user' in all_cookies:
            is_signed = True
            print("sign-in ok: user cookie present")
        else:
            print("user cookie not found; cookies:", list(all_cookies.keys()))
    except Exception as exc:
        print("check cookie fail:", exc)
    print("is_signed:", is_signed)

    if not is_signed:
        print("!! not signed in yet, keep waiting 6s ...")
        time.sleep(6)

    print("=== [3/4] navigate to activity page ===")
    try:
        driver.get(ACTIVITY_URL)
        time.sleep(4)
    except Exception as exc:
        print("navigate activity fail:", exc)

    print("=== [4/4] dispatch loop (mimic chrome_tixcraft main loop) ===")
    start = time.time()
    last_url = ""
    reached_confirm_at = None
    while True:
        time.sleep(0.1)
        try:
            url = driver.current_url
        except Exception as exc:
            print("get url fail:", exc)
            time.sleep(1)
            continue
        if url is None:
            continue
        if url != last_url:
            print("url:", url)
            last_url = url
        if 'ticketplus.com' in url:
            bot.ticketplus_main(driver, url, config_dict, None, None)

        if '/confirm' in url:
            if reached_confirm_at is None:
                reached_confirm_at = time.time()
                print("=== reached confirm page, simulation end (hold browser %ss) ==="
                      % CONFIRM_HOLD_SECONDS)
            if time.time() - reached_confirm_at > CONFIRM_HOLD_SECONDS:
                break

        if time.time() - start > MAX_RUN_SECONDS:
            print("=== reach MAX_RUN_SECONDS, stop ===")
            break

    try:
        driver.quit()
    except Exception as exc:
        print("quit driver fail:", exc)
    print("=== simulation finished ===")


if __name__ == "__main__":
    main()
