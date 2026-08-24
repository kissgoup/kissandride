#!/usr/bin/env python3
#encoding=utf-8
# 單元級驗證: 排隊階段診斷儀器 + 防誤重整欄。
#   G1 送出時間戳換算(_recent_submit_seconds)
#   G2 心跳節奏決策(_queue_heartbeat_state)
#   G3 press_next_step 成功時記錄時間戳
#   G4 press_next_step 失敗時不記錄
#   G5 防誤重整決策(_refresh_blocked_by_queue)
#   Q1~Q4 排隊文字判定(_text_indicates_ticketplus_queue)
#   Q5 排隊轉圈在頁面上時不重按送出(2026-08-24 實測:狂印 submit、把自己踢回隊尾)
#   Q6 無排隊轉圈時照常送出(既有行為不回歸)
import sys
import time as real_time_mod

import chrome_tixcraft as bot


class FakeBody:
    def __init__(self, text):
        self.text = text


def base_config(area_enable=True, ocr_enable=True):
    return {
        "advanced": {"verbose": False},
        "area_auto_select": {"enable": area_enable, "mode": "random", "area_keyword": ""},
        "ticket_number": 2,
        "keyword_exclude": "",
        "ocr_captcha": {"enable": ocr_enable, "force_submit": True, "image_source": "canvas"},
    }


class FakeNextButton:
    def __init__(self):
        self.click_count = 0
    def is_enabled(self):
        return True
    def click(self):
        self.click_count += 1


class OrderDriver:
    def __init__(self, next_button=None, has_captcha=False, body_text=""):
        self.next_button = next_button
        self.has_captcha = has_captcha
        self.body_text = body_text
    def find_element(self, by, css):
        if css == 'input[placeholder="請輸入驗證碼"]':
            if self.has_captcha:
                return object()
            raise Exception("no such element")
        if css == "body":
            return FakeBody(self.body_text)
        if css == "div.order-footer > div.container > div.row > div > button.nextBtn":
            if self.next_button is not None:
                return self.next_button
            raise Exception("no such element")
        raise Exception("no such element: %s" % css)
    def execute_script(self, *args, **kwargs):
        return None
    def set_script_timeout(self, t):
        pass


results = []
NOW = 1000000.0

# G1 _recent_submit_seconds
ok = bot._recent_submit_seconds({}, NOW) is None
print("[G1a no marker -> None] -> %s" % ("PASS" if ok else "FAIL")); results.append(ok)

ok = bot._recent_submit_seconds({"last_next_press_time": NOW - 45}, NOW) == 45
print("[G1b 45s ago -> 45] -> %s" % ("PASS" if ok else "FAIL")); results.append(ok)

ok = bot._recent_submit_seconds({"last_next_press_time": NOW - 400}, NOW) is None
print("[G1c beyond guard window -> None] -> %s" % ("PASS" if ok else "FAIL")); results.append(ok)

# G2 _queue_heartbeat_state
due, elapsed = bot._queue_heartbeat_state(NOW, NOW - 45, 0.0)
ok = (due is True) and (elapsed == 45)
print("[G2a due when interval passed] -> %s" % ("PASS" if ok else "FAIL")); results.append(ok)

due, elapsed = bot._queue_heartbeat_state(NOW, NOW - 45, NOW - 5)
ok = (due is False)
print("[G2b silent within interval] -> %s" % ("PASS" if ok else "FAIL")); results.append(ok)

due, elapsed = bot._queue_heartbeat_state(NOW, NOW - 1000, 0.0)
ok = (due is False)
print("[G2c silent beyond window] -> %s" % ("PASS" if ok else "FAIL")); results.append(ok)

# G3/G4 press_next_step 記錄時間戳
_real_time = bot.time.time
_real_sleep = bot.time.sleep
bot.time.time = lambda: NOW
bot.time.sleep = lambda s: None
try:
    td = {}
    ret = bot.ticketplus_press_next_step(OrderDriver(next_button=FakeNextButton()), base_config(), None, None, td)
    ok = (ret is True) and (td.get("last_next_press_time") == NOW)
    print("[G3 success records timestamp] -> %s" % ("PASS" if ok else "FAIL")); results.append(ok)

    td = {}
    ret = bot.ticketplus_press_next_step(OrderDriver(next_button=None), base_config(), None, None, td)
    ok = (ret is False) and ("last_next_press_time" not in td)
    print("[G4 failure records nothing] -> %s" % ("PASS" if ok else "FAIL")); results.append(ok)
finally:
    bot.time.time = _real_time
    bot.time.sleep = _real_sleep

# G5 _refresh_blocked_by_queue
ok = bot._refresh_blocked_by_queue({"last_next_press_time": NOW - 10}, NOW) is True
print("[G5a recent submit blocks refresh] -> %s" % ("PASS" if ok else "FAIL")); results.append(ok)

ok = bot._refresh_blocked_by_queue({}, NOW) is False
print("[G5b no marker allows refresh] -> %s" % ("PASS" if ok else "FAIL")); results.append(ok)

ok = bot._refresh_blocked_by_queue(None, NOW) is False
print("[G5c None dict allows refresh] -> %s" % ("PASS" if ok else "FAIL")); results.append(ok)

# Q1~Q4 排隊文字判定
ok = bot._text_indicates_ticketplus_queue("排隊購票中 請稍候") is True
print("[Q1 queue text detected] -> %s" % ("PASS" if ok else "FAIL")); results.append(ok)

ok = bot._text_indicates_ticketplus_queue("系統安排座位中,請稍候") is True
print("[Q2 seat-arrange text detected] -> %s" % ("PASS" if ok else "FAIL")); results.append(ok)

ok = bot._text_indicates_ticketplus_queue("R2區 剩餘 5 NT.5,800 全票 下一步") is False
print("[Q3 normal order text ignored] -> %s" % ("PASS" if ok else "FAIL")); results.append(ok)

ok = (bot._text_indicates_ticketplus_queue("") is False) and (bot._text_indicates_ticketplus_queue(None) is False)
print("[Q4 empty/None safe] -> %s" % ("PASS" if ok else "FAIL")); results.append(ok)

# Q5 排隊轉圈存在時,即使按鈕 enabled 也不得重按送出
btn = FakeNextButton()
td = {}
bot.ticketplus_order(
    OrderDriver(next_button=btn, body_text="排隊購票中 請稍候 R2區 剩餘 5"),
    base_config(), None, None, td)
ok = (btn.click_count == 0) and ("last_next_press_time" not in td)
print("[Q5 no re-submit while queued] -> %s" % ("PASS" if ok else "FAIL")); results.append(ok)

# Q6 無排隊轉圈時,enabled 按鈕照常送出(既有行為)
btn = FakeNextButton()
td = {}
bot.time.time = lambda: NOW
bot.time.sleep = lambda s: None
try:
    bot.ticketplus_order(
        OrderDriver(next_button=btn, body_text="票區一覽 R2區 剩餘 5 全票 NT. 5,800"),
        base_config(), None, None, td)
finally:
    bot.time.time = _real_time
    bot.time.sleep = _real_sleep
ok = (btn.click_count == 1) and (td.get("last_next_press_time") == NOW)
print("[Q6 normal page still submits] -> %s" % ("PASS" if ok else "FAIL")); results.append(ok)

# Q7 送出後短窗內(文字消失、導航未完成的過渡期),enabled 按鈕不得自動重按
btn = FakeNextButton()
td = {"last_next_press_time": NOW - 15}
bot.time.time = lambda: NOW
try:
    bot.ticketplus_order(
        OrderDriver(next_button=btn, body_text="票區一覽 R2區 剩餘 5"),
        base_config(), None, None, td)
finally:
    bot.time.time = _real_time
    bot.time.sleep = _real_sleep
ok = btn.click_count == 0
print("[Q7 repress suppressed right after submit] -> %s" % ("PASS" if ok else "FAIL")); results.append(ok)

# Q8 短窗外(45 秒),enabled 按鈕恢復自動送出
btn = FakeNextButton()
td = {"last_next_press_time": NOW - 45}
bot.time.time = lambda: NOW
bot.time.sleep = lambda s: None
try:
    bot.ticketplus_order(
        OrderDriver(next_button=btn, body_text="票區一覽 R2區 剩餘 5"),
        base_config(), None, None, td)
finally:
    bot.time.time = _real_time
    bot.time.sleep = _real_sleep
ok = btn.click_count == 1
print("[Q8 repress allowed after suppress window] -> %s" % ("PASS" if ok else "FAIL")); results.append(ok)

print("----")
print("ALL PASS" if all(results) else "SOME FAILED")
real_time_mod.sleep(0)
sys.exit(0 if all(results) else 1)
