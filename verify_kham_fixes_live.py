#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Live verification of both kham fixes against real pages.

Phase 1 (bug #1): open UTK0201_ (step-1), run hkam_date_auto_select with the
    real settings.json config (keyword_exclude contains "4680"). Expect the
    function to pick a date and click 立即訂購 (is_date_assign=True).

Phase 2 (bug #2): navigate to the real UTK0205_ (step-3) and run the fixed
    kham_keyin_captcha_code(driver, "A1B2"). Expect #CHK value == "A1B2".
"""
import json
import sys
import time
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By

import chrome_tixcraft as bot
import util

STEP1_URL = "https://kham.com.tw/application/UTK02/UTK0201_00.aspx?PRODUCT_ID=P1D3G65D"
STEP3_URL = ("https://kham.com.tw/application/UTK02/UTK0205_.aspx?PERFORMANCE_ID=P1D430L4"
             "&GROUP_ID=16&PERFORMANCE_PRICE_AREA_ID=P1DA05FM")

def build_config():
    s = json.load(open("settings.json", encoding="utf-8"))
    return {
        "advanced": {"verbose": True, "auto_reload_page_interval": 0},
        "date_auto_select": {"mode": bot.CONST_FROM_TOP_TO_BOTTOM,
                             "date_keyword": s["date_auto_select"]["date_keyword"]},
        "area_auto_select": {"mode": bot.CONST_RANDOM, "area_keyword": ""},
        "ticket_number": 2,
        "keyword_exclude": s["keyword_exclude"],
        "tixcraft": {"auto_reload_coming_soon_page": False},
    }

def main():
    driver = uc.Chrome(headless=False)
    try:
        config = build_config()
        print("keyword_exclude:", config["keyword_exclude"])

        # ---- Phase 1: step-1 date select ----
        print("\n========== PHASE 1: step-1 date select ==========")
        driver.get(STEP1_URL)
        time.sleep(2)
        is_date_assign = bot.hkam_date_auto_select(driver, "kham.com.tw", config)
        print("is_date_assign:", is_date_assign)
        print("url after:", driver.current_url[:100])
        time.sleep(2)
        if ".aspx?performance_id=" in driver.current_url.lower():
            print("PHASE 1 OK: advanced to step-2 (area page)")
        else:
            print("PHASE 1 WARN: did not advance (url=%s)" % driver.current_url[:100])

        # ---- Phase 2: step-3 captcha fill ----
        print("\n========== PHASE 2: step-3 captcha fill ==========")
        driver.get(STEP3_URL)
        time.sleep(2)
        chk = driver.find_element(By.CSS_SELECTOR, "input#CHK")
        print("before: #CHK value = %r" % chk.get_attribute("value"))

        is_editing = bot.kham_keyin_captcha_code(driver, answer="A1B2", auto_submit=False)
        chk2 = driver.find_element(By.CSS_SELECTOR, "input#CHK")
        actual = chk2.get_attribute("value")
        print("after:  #CHK value = %r (expect 'A1B2')" % actual)
        if actual == "A1B2":
            print("PHASE 2 OK: captcha filled via fixed function")
        else:
            print("PHASE 2 FAIL: captcha not filled")

    finally:
        driver.quit()

if __name__ == "__main__":
    main()
