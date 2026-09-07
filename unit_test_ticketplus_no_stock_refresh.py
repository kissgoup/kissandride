#!/usr/bin/env python3
#encoding=utf-8
# 單元級驗證: ticketplus /order/「無可販售/殘數過期/等待」態的重查決策。
#   S1 interval<=0 (feature off) -> False、不點不刷
#   S2 settle 窗: 新 URL 首次呼叫 -> False (開始計時)；未滿 1.5s -> False；已過 -> 動作
#   S3 有「更新票數」-> JS 點它(不整頁 reload)
#   S4 無「更新票數」-> driver.refresh()
#   S5 dialog 開著 -> 不動作
#   S6 force=True 略過 settle/上一輪 refresh 標記
#   S7 上一輪 expansion 剛 refresh (expansion_refreshed_at 新鮮) -> 同輪不再刷
#   C1 ticketplus_click_refresh_count_button: 找得到 -> True 且按下
#   C2 ticketplus_click_refresh_count_button: 找不到 -> False
#   JS CONST: 找按鈕的 JS 限定可點擊(排除 disabled/v-btn--disabled/aria-disabled)、文字含更新票數
import sys
import time as real_time_mod

import chrome_tixcraft as bot


class FakeRefreshElement:
    pass


class FakeDriver:
    def __init__(self, url="https://ticketplus.com.tw/order/a/b",
                 has_button=True, dialogs=None):
        self.current_url = url
        self.has_button = has_button
        self.dialogs = dialogs if dialogs is not None else []
        self.refresh_count = 0
        self.click_count = 0

    def find_elements(self, by, css):
        if css == 'div[role="dialog"]':
            return [1] * len(self.dialogs)
        return []

    def execute_script(self, code, *args):
        if code == bot.CONST_TICKETPLUS_REFRESH_COUNT_FIND_JS:
            if self.has_button:
                return FakeRefreshElement()
            return None
        if code.startswith("arguments[0].click();"):
            if isinstance(args[0], FakeRefreshElement):
                self.click_count += 1
            return None
        return None

    def refresh(self):
        self.refresh_count += 1


def no_stock_config(interval=0.1):
    return {"advanced": {"auto_reload_page_interval": interval}}


def settled_dict(url="https://ticketplus.com.tw/order/a/b", seconds_ago=2.0):
    # 已超過 settle 窗的 dict 狀態。
    return {"no_stock_url": url, "no_stock_since": real_time_mod.time() - seconds_ago}


results = []

# S1 interval<=0 (feature off)
d = FakeDriver(has_button=True)
ret = bot.ticketplus_order_no_stock_refresh(d, no_stock_config(0), {}, force=True)
ok = ret is False and d.click_count == 0 and d.refresh_count == 0
print("[S1 interval 0 no-op] -> %s" % ("PASS" if ok else "FAIL")); results.append(ok)

# S2 新 URL 首次 -> 開始計時 False(不動作)
d = FakeDriver(has_button=False)
td = {}
ret = bot.ticketplus_order_no_stock_refresh(d, no_stock_config(), td)
ok = ret is False and d.refresh_count == 0 and td.get("no_stock_url") == d.current_url
print("[S2 new url start settle] -> %s" % ("PASS" if ok else "FAIL")); results.append(ok)

# S2 未滿 1.5s -> False
d = FakeDriver(has_button=False)
td = settled_dict(seconds_ago=0.4)
ret = bot.ticketplus_order_no_stock_refresh(d, no_stock_config(), td)
ok = ret is False and d.refresh_count == 0
print("[S2 within settle window] -> %s" % ("PASS" if ok else "FAIL")); results.append(ok)

# S2 已過 settle + 無按鈕 -> 整頁 reload、回 True
d = FakeDriver(has_button=False)
td = settled_dict()
ret = bot.ticketplus_order_no_stock_refresh(d, no_stock_config(), td)
ok = ret is True and d.refresh_count == 1 and d.click_count == 0
print("[S2 past settle reload] -> %s" % ("PASS" if ok else "FAIL")); results.append(ok)

# S3 有「更新票數」-> 點它、不 reload
d = FakeDriver(has_button=True)
td = settled_dict()
ret = bot.ticketplus_order_no_stock_refresh(d, no_stock_config(), td)
ok = ret is True and d.click_count == 1 and d.refresh_count == 0
print("[S3 click 更新票數] -> %s" % ("PASS" if ok else "FAIL")); results.append(ok)

# S5 dialog 開著 -> 不動作(即使有按鈕/已過 settle)
d = FakeDriver(has_button=True, dialogs=["x"])
td = settled_dict()
ret = bot.ticketplus_order_no_stock_refresh(d, no_stock_config(), td)
ok = ret is False and d.click_count == 0 and d.refresh_count == 0
print("[S5 dialog open no-op] -> %s" % ("PASS" if ok else "FAIL")); results.append(ok)

# S6 force=True 略過 settle：新 URL 也立刻動作
d = FakeDriver(has_button=True)
ret = bot.ticketplus_order_no_stock_refresh(d, no_stock_config(), {}, force=True)
ok = ret is True and d.click_count == 1
print("[S6 force bypass settle] -> %s" % ("PASS" if ok else "FAIL")); results.append(ok)

# S6b force=True 且無按鈕 -> 直接 reload
d = FakeDriver(has_button=False)
ret = bot.ticketplus_order_no_stock_refresh(d, no_stock_config(), {}, force=True)
ok = ret is True and d.refresh_count == 1
print("[S6b force reload] -> %s" % ("PASS" if ok else "FAIL")); results.append(ok)

# S7 上一輪 expansion 剛 refresh（expansion_refreshed_at 新鮮）-> 同輪不再刷
d = FakeDriver(has_button=False)
td = settled_dict()
td["expansion_refreshed_at"] = real_time_mod.time()
ret = bot.ticketplus_order_no_stock_refresh(d, no_stock_config(), td)
ok = ret is False and d.refresh_count == 0
print("[S7 fresh expansion refresh skip] -> %s" % ("PASS" if ok else "FAIL")); results.append(ok)

# C1 click helper 找得到 -> True 且按下
d = FakeDriver(has_button=True)
ok = bot.ticketplus_click_refresh_count_button(d) is True and d.click_count == 1
print("[C1 click helper found] -> %s" % ("PASS" if ok else "FAIL")); results.append(ok)

# C2 click helper 找不到 -> False
d = FakeDriver(has_button=False)
ok = bot.ticketplus_click_refresh_count_button(d) is False
print("[C2 click helper not found] -> %s" % ("PASS" if ok else "FAIL")); results.append(ok)

# JS CONST 設計斷言
js = bot.CONST_TICKETPLUS_REFRESH_COUNT_FIND_JS
ok = ("更新票數" in js and "el.disabled" in js and "v-btn--disabled" in js
      and "aria-disabled" in js and "[role=\"button\"]" in js)
print("[JS finder clickable-only + text] -> %s" % ("PASS" if ok else "FAIL")); results.append(ok)

ok = bot.CONST_TICKETPLUS_NO_STOCK_SETTLE_SECONDS > 0
print("[JS/const settle defined] -> %s" % ("PASS" if ok else "FAIL")); results.append(ok)

print("----")
print("ALL PASS" if all(results) else "SOME FAILED")
real_time_mod.sleep(0)
sys.exit(0 if all(results) else 1)
