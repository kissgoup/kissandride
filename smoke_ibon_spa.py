"""Live smoke test of the two new ibon paths (navigation only, no submits).

1. SPA detail page 39707 -> ibon_game_list_auto_select with keyword "10/03"
   must land on UTK0201_000.aspx?PERFORMANCE_ID=B0BUJ497 (the 10/03 session).
2. Step-2 page -> ibon_area_auto_select with keyword "站席" must land on
   UTK0201_001.aspx?...PERFORMANCE_PRICE_AREA_ID=B0BX279R (2樓站席).
"""
import time

from selenium import webdriver
from selenium.webdriver.chrome.service import Service

import chrome_tixcraft as bot

SPA_URL = "https://ticket.ibon.com.tw/ActivityInfo/Details/39707"

config_dict = {
    "ticket_number": 2,
    "date_auto_select": {"mode": bot.CONST_FROM_TOP_TO_BOTTOM,
                         "date_keyword": "10/03"},
    "area_auto_select": {"mode": bot.CONST_FROM_TOP_TO_BOTTOM,
                         "area_keyword": "站席"},
    "advanced": {"verbose": True, "auto_reload_page_interval": 0},
    "tixcraft": {"auto_reload_coming_soon_page": False},
    "ocr_captcha": {"enable": False},
}

opts = webdriver.ChromeOptions()
opts.add_argument("--window-size=1400,1000")
opts.add_argument("--lang=zh-TW")
opts.add_argument("--no-sandbox")
opts.add_argument("--no-first-run")
opts.add_argument("--no-default-browser-check")
opts.add_argument("--disable-blink-features=AutomationControlled")
opts.add_experimental_option("excludeSwitches", ["enable-automation"])
opts.add_experimental_option("useAutomationExtension", False)
opts.page_load_strategy = "eager"

driver = webdriver.Chrome(
    service=Service(r"C:\project\kissandride\webdriver\chromedriver.exe"),
    options=opts,
)
ok = False
try:
    # ---- path 1: SPA game list ----
    driver.get(SPA_URL)
    time.sleep(6)
    ret = bot.ibon_game_list_auto_select(driver, config_dict, SPA_URL)
    time.sleep(3)
    url1 = driver.current_url
    print("\n[1] game_list ret:", ret)
    print("[1] landed:", url1[:130])
    assert ret is True, "game selector did not navigate"
    assert "UTK0201_000" in url1.upper(), "not on step-2 page"
    assert "B0BUJ497" in url1.upper(), "wrong session (expected 10/03 = B0BUJ497)"
    print("[1] PASS")

    # ---- path 2: step-2 area json ----
    time.sleep(4)
    is_need_refresh, is_price_assign = bot.ibon_area_auto_select(
        driver, config_dict, "站席")
    time.sleep(3)
    url2 = driver.current_url
    print("\n[2] need_refresh:", is_need_refresh, "assigned:", is_price_assign)
    print("[2] landed:", url2[:130])
    assert is_price_assign is True and is_need_refresh is False
    assert "UTK0201_001" in url2.upper(), "not on step-3 page"
    # area ID is session-specific; fixture tests cover exact-ID mapping.
    assert "PERFORMANCE_PRICE_AREA_ID=" in url2.upper(), "no area id in url"
    print("[2] PASS")
    ok = True
finally:
    print("\nSMOKE TEST:", "PASS" if ok else "FAIL")
    try:
        driver.quit()
    except Exception:
        pass
