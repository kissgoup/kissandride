#!/usr/bin/env python3
#encoding=utf-8
# 整合驗證：用有頭 undetected_chromedriver 開真實 tixcraft 區域頁，
# 確認 get_tixcraft_target_area 在實際 DOM 上能正確過濾剩餘張數不足的區域。
# 需要連外網路；tixcraft epsf 防護會擋 headless，所以用有頭模式。
import time

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By

import chrome_tixcraft as bot

TARGET_URL = "https://tixcraft.com/ticket/area/26_5sos/23045"
TICKET_NUMBER = 2  # 買 2 張：剩餘 1 的區應被排除


def main():
    driver = uc.Chrome(headless=False)
    try:
        driver.get(TARGET_URL)
        print("title:", driver.title)

        zone_el = None
        for _ in range(45):
            try:
                zone_el = driver.find_element(By.CSS_SELECTOR, '.zone')
                break
            except Exception:
                time.sleep(1)
        if zone_el is None:
            print("FAIL: 找不到 .zone，可能被 epsf 防護攔截")
            return

        config = {
            "advanced": {"verbose": True},
            "area_auto_select": {"mode": bot.CONST_RANDOM, "area_keyword": ""},
            "ticket_number": TICKET_NUMBER,
            "keyword_exclude": "",
        }
        is_need_refresh, matched_blocks = bot.get_tixcraft_target_area(zone_el, config, "")
        print("is_need_refresh:", is_need_refresh)
        if matched_blocks is None:
            print("matched_blocks: None")
            return
        print("matched count:", len(matched_blocks))
        remaining_set = set()
        for row in matched_blocks:
            text = row.text
            try:
                font_el = row.find_element(By.TAG_NAME, 'font')
                remaining = bot.parse_tixcraft_area_remaining(font_el.text)
            except Exception:
                remaining = None
            remaining_set.add(remaining)
            print("  [remaining=%s] %s" % (remaining, text))
        print("剩餘張數集合:", remaining_set)
        bad = {r for r in remaining_set if r is not None and r < TICKET_NUMBER}
        assert not bad, "不應出現剩餘張數 < %d 的區域，實際: %s" % (TICKET_NUMBER, sorted(bad))
        print("\nPASS: 買 %d 張時，實際 DOM 上的過濾行為正確" % TICKET_NUMBER)
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
