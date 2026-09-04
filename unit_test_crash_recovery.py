#!/usr/bin/env python3
#encoding=utf-8
# 單元級驗證: 分頁崩潰偵測與復原(2026-09-04 實測: ticketplus /order/ 頁分頁
# crashed 後 bot 只會無限印例外、不刷新不重試)。
#   C1 崩潰訊息偵測(_is_crashed_tab_error)
#   C2 正常例外不算崩潰
#   C3 復原成功: driver.get(最後已知網址)喚醒已崩分頁
#   C4 復原失敗(driver 徹底死亡): 回傳 False,交給上層退出/重啟
#   C5 read_last_url_from_file 不可用時退避 about:blank
import sys

import chrome_tixcraft as bot


class RevivableDriver:
    """模擬 'tab crashed' 的分頁: current_url 會炸, 直到 driver.get() 喚醒。"""
    def __init__(self, alive=False, handles=("w1",)):
        self.alive = alive
        self.handles = handles
        self.navigated = None
        self.switched = []
        self.current_url = None
    @property
    def window_handles(self):
        return list(self.handles)
    def switch_to_window(self, handle):
        self.switched.append(handle)
    def get(self, url):
        self.navigated = url
        self.alive = True
    def refresh(self):
        self.alive = True
    def _read_current_url(self):
        if not self.alive:
            raise Exception("no such execution context: tab crashed")
        return self.current_url or ("https://ticketplus.com.tw/order/e/s" if self.navigated else "")


class DeadDriver(RevivableDriver):
    """driver.get() 也救不回(整個 session 掛掉)。"""
    def get(self, url):
        self.navigated = url
        raise Exception("chrome not reachable")


results = []
N = 0

# C1 崩潰訊息偵測
for probe, expect in [("tab crashed", True), ("no such execution context", True),
                      ("detached from a live document", True),
                      ("其他網路錯誤 connection refused", False),
                      ("", False), (None, False)]:
    ok = bot._is_crashed_tab_error(probe) is expect
    print("[C1 %r -> %s] -> %s" % (str(probe)[:30], expect, "PASS" if ok else "FAIL"))
    results.append(ok)

# C2 正常例外(如按鈕 not clickable)不算崩潰
ok = bot._is_crashed_tab_error("element click intercepted") is False
print("[C2 normal exception not crash] -> %s" % ("PASS" if ok else "FAIL")); results.append(ok)

# C3 復原成功: driver.get(最後已知網址)喚醒
_real_read = bot.read_last_url_from_file
bot.read_last_url_from_file = lambda: "https://ticketplus.com.tw/order/e/s"
try:
    d = RevivableDriver(alive=False)
    ok = bot._try_recover_crashed_tab(d) is True
    ok = ok and (d.navigated == "https://ticketplus.com.tw/order/e/s")
finally:
    bot.read_last_url_from_file = _real_read
print("[C3 recovery via get(last url)] -> %s" % ("PASS" if ok else "FAIL")); results.append(ok)

# C4 復原失敗
d = DeadDriver(alive=False)
ok = bot._try_recover_crashed_tab(d) is False
print("[C4 dead driver not recoverable] -> %s" % ("PASS" if ok else "FAIL")); results.append(ok)

# C5 無最後網址檔時退避 about:blank
_real_read = bot.read_last_url_from_file
bot.read_last_url_from_file = lambda: ""
try:
    d = RevivableDriver(alive=False)
    ok = bot._try_recover_crashed_tab(d) is True
    ok = ok and (d.navigated == "about:blank")
finally:
    bot.read_last_url_from_file = _real_read
print("[C5 fallback about:blank] -> %s" % ("PASS" if ok else "FAIL")); results.append(ok)

print("----")
print("ALL PASS" if all(results) else "SOME FAILED")
sys.exit(0 if all(results) else 1)
