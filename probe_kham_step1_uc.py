#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Diagnose why hkam_date_auto_select returns 'not found date-time-position'
when run with undetected_chromedriver (same as the real bot).

Steps:
  1. Open UTK0201_00.aspx with uc.Chrome(headless=False) — same options as bot
  2. Dump raw innerHTML of every <tr> in table.eventTABLE
  3. Apply each filter condition from hkam_date_auto_select and print why row dies
  4. Print final matched blocks count
"""
import json
import re
import time
import sys
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By

import chrome_tixcraft as bot
import util


TARGET_URL = "https://kham.com.tw/application/UTK02/UTK0201_00.aspx?PRODUCT_ID=P1D3G65D"

# real settings.json values
with open("settings.json", encoding="utf-8") as f:
    _s = json.load(f)
config = {
    "advanced": {"verbose": True},
    "date_auto_select": {"mode": bot.CONST_FROM_TOP_TO_BOTTOM, "date_keyword": _s["date_auto_select"]["date_keyword"]},
    "area_auto_select": {"mode": bot.CONST_RANDOM, "area_keyword": ""},
    "ticket_number": 2,
    "keyword_exclude": _s["keyword_exclude"],
    "tixcraft": {"auto_reload_coming_soon_page": False},
}

def main():
    driver = uc.Chrome(headless=False)
    try:
        driver.get(TARGET_URL)
        print("title:", driver.title)

        # Wait for table.eventTABLE
        wait_time = 20
        elapsed = 0
        rows_el = []
        while elapsed < wait_time:
            try:
                rows_el = driver.find_elements(By.CSS_SELECTOR, "table.eventTABLE > tbody > tr")
                if len(rows_el) > 1:
                    break
            except Exception:
                pass
            time.sleep(0.5)
            elapsed += 0.5

        print(f"\nFound {len(rows_el)} rows in table.eventTABLE > tbody > tr")

        # Dump all rows
        for i, row in enumerate(rows_el):
            html = row.get_attribute('innerHTML') or ""
            text = util.remove_html_tags(html)
            has_btn = '<button' in html
            is_disabled = ('disabled>' in html) or ('"disabled"' in html)
            print(f"\n--- Row {i} ({len(html)} chars) ---")
            print(f"  text[:120]: {repr(text[:120])}")
            print(f"  has button: {has_btn}")
            print(f"  disabled: {is_disabled}")

            # Simulate HKAM filter step by step
            keep = True
            if len(text) == 0:
                print("  FATAL: row_text is empty")
                keep = False

            if keep:
                exclude = config["keyword_exclude"]
                print("  keyword_exclude:", repr(exclude))
                matched = util.reset_row_text_if_match_keyword_exclude(config, text)
                if matched:
                    print("  FILTERED: keyword_exclude match")
                    keep = False

            if keep:
                has_btn = '<button' in html
                if has_btn:
                    if ' disabled">' in html or '"disabled"' in html:
                        print("  FILTERED: button disabled")
                        keep = False
                else:
                    print("  FILTERED: no <button> tag")
                    keep = False

            if keep:
                if '<button' in html:
                    buyable = ('立即訂購' in text) or ('點此購票' in text)
                    if not buyable:
                        print("  FILTERED: buyable keyword not found (text=%s)" % repr(text[:60]))
                        keep = False
                else:
                    print("  FILTERED: no <button>")
                    keep = False

            if keep:
                # price check (kham-specific)
                td_array = html.split("<td")
                if len(td_array) > 3:
                    td_target = td_array[3]
                    price_array = td_target.split("、")
                    all_disabled = True
                    for p in price_array:
                        if not ('"lightblue"' in p or 'lightblue' in p):
                            all_disabled = False
                    if all_disabled:
                        prices_display = []
                        for p in price_array[:4]:
                            pt = re.sub(r"<[^>]+>", "", p)[:30].strip()
                            sold_out = ('lightblue' in p or '<s>' in p)
                            prices_display.append("%s SOLDOUT" % pt if sold_out else "%s OK" % pt)
                        print("  FILTERED: ALL PRICES SOLD OUT (%s)" % " | ".join(prices_display))
                        keep = False
                    else:
                        print("  PASS: has non-soldout price")

            if keep:
                fmt = util.format_keyword_string(text)
                print("  FORMATTED MATCHES DATE_KEYWORD")
            else:
                print("  EXCLUDED by some filter above")

        print("\n\n=== Running actual hkam_date_auto_select (real settings) ===")
        result = bot.hkam_date_auto_select(driver, "kham.com.tw", config)
        print("RESULT is_date_assign_by_bot:", result)

        print("\n=== Checking current URL after hkam call ===")
        print("current_url:", driver.current_url)

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
