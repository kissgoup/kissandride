#!/usr/bin/env python3
#encoding=utf-8
# 單元級驗證: ticketplus 四項修正。
#   #1 有驗證碼欄位時走 OCR 鏈，否則直接按下一步（接回 ticketplus_order_ocr）
#   #2 /order/ 尊重 area_auto_select.enable
#   #3 nextBtn 已 enabled 時冷卻送出（不再永久停等）
#   #4 同意勾選掃全部 checkbox
# 不啟動瀏覽器，使用 fake driver/button/checkbox。
import sys
import time as real_time_mod

import chrome_tixcraft as bot

NEXT_STYLE2 = "div.order-footer > div.container > div.row > div > button.nextBtn"
CAPTCHA_SELECTOR = 'input[placeholder="請輸入驗證碼"]'


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


class FakeDisabledButton:
    def __init__(self):
        self.click_count = 0
    def is_enabled(self):
        return False
    def click(self):
        self.click_count += 1


class FakeCheckbox:
    def __init__(self, selected=False, fail_click=False):
        self.selected = selected
        self.fail_click = fail_click
        self.click_count = 0
    def is_enabled(self):
        return True
    def is_selected(self):
        return self.selected
    def click(self):
        self.click_count += 1
        if self.fail_click:
            raise Exception("native click blocked")
        self.selected = True


class OrderDriver:
    """fake driver for ticketplus_order / ticketplus_press_next_step."""
    def __init__(self, next_button=None, has_captcha=False):
        self.next_button = next_button
        self.has_captcha = has_captcha
        self.calls = []
    def find_element(self, by, css):
        self.calls.append(css)
        if css == CAPTCHA_SELECTOR:
            if self.has_captcha:
                return object()
            raise Exception("no such element")
        if css == NEXT_STYLE2:
            if self.next_button is not None:
                return self.next_button
            raise Exception("no such element")
        raise Exception("no such element: %s" % css)
    def find_elements(self, by, css):
        return []
    def execute_script(self, *args, **kwargs):
        return None
    def set_script_timeout(self, t):
        pass


class AgreeDriver:
    """fake driver for ticketplus_ticket_agree."""
    def __init__(self, boxes, js_fail=False):
        self.boxes = boxes
        self.js_fail = js_fail
    def find_elements(self, by, css):
        return self.boxes
    def execute_script(self, *args, **kwargs):
        if self.js_fail:
            raise Exception("js click blocked")
        return None


results = []

# ---------------------------------------------------------------
# #2 area_auto_select.enable=false -> 不碰 driver, 直接返回
# ---------------------------------------------------------------
d = OrderDriver(next_button=FakeNextButton())
ret = bot.ticketplus_order(d, base_config(area_enable=False), None, None, {})
ok = (len(d.calls) == 0)
print("[#2 area disabled -> no interaction] calls=%d -> %s" % (len(d.calls), "PASS" if ok else "FAIL"))
results.append(ok)

# ---------------------------------------------------------------
# #3a 抵達時 nextBtn 已 enabled -> 應直接送出(不再停等)
# ---------------------------------------------------------------
btn = FakeNextButton()
d = OrderDriver(next_button=btn)
cfg = base_config()
tdict = {}
now = [1000.0]
_real_time = bot.time.time
_real_sleep = bot.time.sleep
bot.time.time = lambda: now[0]
bot.time.sleep = lambda s: now.__setitem__(0, now[0] + s)
try:
    bot.ticketplus_order(d, cfg, None, None, tdict)
    ok = (btn.click_count == 1)
    print("[#3a ready button -> submit] clicks=%d -> %s" % (btn.click_count, "PASS" if ok else "FAIL"))
    results.append(ok)

    # #3b 冷卻時間內重複進入 -> 不重複送出
    bot.ticketplus_order(d, cfg, None, None, tdict)
    ok = (btn.click_count == 1)
    print("[#3b cooldown blocks re-submit] clicks=%d -> %s" % (btn.click_count, "PASS" if ok else "FAIL"))
    results.append(ok)

    # #3c 送出後 10 秒(排隊尾端過渡期,spinner 文字已消失) -> 不得自動重按
    #     (2026-08-24 實測:該重按會把訂單踢回隊尾,改由 30 秒抑制窗涵蓋)
    now[0] += 10.0
    bot.ticketplus_order(d, cfg, None, None, tdict)
    ok = (btn.click_count == 1)
    print("[#3c repress suppressed at +10s] clicks=%d -> %s" % (btn.click_count, "PASS" if ok else "FAIL"))
    results.append(ok)

    # #3c-2 抑制窗外(45 秒) -> 恢復可再次送出
    now[0] += 35.0
    bot.ticketplus_order(d, cfg, None, None, tdict)
    ok = (btn.click_count == 2)
    print("[#3c2 re-submit after suppress window] clicks=%d -> %s" % (btn.click_count, "PASS" if ok else "FAIL"))
    results.append(ok)
finally:
    bot.time.time = _real_time
    bot.time.sleep = _real_sleep

# ---------------------------------------------------------------
# #3d disabled 按鈕但選不到票區 -> 維持不送出(回歸保護)
# ---------------------------------------------------------------
btn_d = FakeDisabledButton()
d = OrderDriver(next_button=btn_d)
tdict = {}
bot.get_random_delay = lambda cfg: 0.0
bot.time.sleep = lambda s: None
bot.ticketplus_order(d, base_config(), None, None, tdict)
ok = (btn_d.click_count == 0)
print("[#3d no match + disabled -> no submit] clicks=%d -> %s" % (btn_d.click_count, "PASS" if ok else "FAIL"))
results.append(ok)

# ---------------------------------------------------------------
# #4 同意勾選掃全部 checkbox
# ---------------------------------------------------------------
b1 = FakeCheckbox()
b2 = FakeCheckbox()
ok = bot.ticketplus_ticket_agree(AgreeDriver([b1, b2]), base_config()) is True
ok = ok and b1.selected and b2.selected and b1.click_count == 1 and b2.click_count == 1
print("[#4a two unchecked -> both checked, True] -> %s" % ("PASS" if ok else "FAIL"))
results.append(ok)

b1 = FakeCheckbox(selected=True)
b2 = FakeCheckbox()
ok = bot.ticketplus_ticket_agree(AgreeDriver([b1, b2]), base_config()) is True
ok = ok and b1.click_count == 0 and b2.selected
print("[#4b one already checked -> only other clicked, True] -> %s" % ("PASS" if ok else "FAIL"))
results.append(ok)

bad = FakeCheckbox(fail_click=True)
good = FakeCheckbox()
d = AgreeDriver([bad, good], js_fail=True)
ok = bot.ticketplus_ticket_agree(d, base_config()) is False
ok = ok and good.selected
print("[#4c unclickable box -> False, others still processed] -> %s" % ("PASS" if ok else "FAIL"))
results.append(ok)

ok = bot.ticketplus_ticket_agree(AgreeDriver([]), base_config()) is False
print("[#4d no checkbox found -> False] -> %s" % ("PASS" if ok else "FAIL"))
results.append(ok)

# ---------------------------------------------------------------
# #1 送出路由: 有驗證碼欄位且 OCR 開啟 -> 走 OCR 鏈；否則直接按下一步
# ---------------------------------------------------------------
ocr_calls = []
_real_ocr = bot.ticketplus_order_ocr
bot.ticketplus_order_ocr = lambda drv, cfg, o, cb: (ocr_calls.append(1) or True)
try:
    # #1a 無驗證碼欄位(就算 OCR 開啟) -> 直接按下一步
    ocr_calls.clear()
    btn = FakeNextButton()
    d = OrderDriver(next_button=btn)
    ret = bot.ticketplus_press_next_step(d, base_config(ocr_enable=True), None, None)
    ok = (ret is True) and (btn.click_count == 1) and (len(ocr_calls) == 0)
    print("[#1a no captcha field -> direct press] ret=%s clicks=%d ocr=%d -> %s"
          % (ret, btn.click_count, len(ocr_calls), "PASS" if ok else "FAIL"))
    results.append(ok)

    # #1b 有驗證碼欄位 + OCR 開啟 -> 交給 ticketplus_order_ocr, 不直接按
    ocr_calls.clear()
    btn = FakeNextButton()
    d = OrderDriver(next_button=btn, has_captcha=True)
    ret = bot.ticketplus_press_next_step(d, base_config(ocr_enable=True), None, None)
    ok = (ret is True) and (btn.click_count == 0) and (len(ocr_calls) == 1)
    print("[#1b captcha + ocr on -> ocr chain] ret=%s clicks=%d ocr=%d -> %s"
          % (ret, btn.click_count, len(ocr_calls), "PASS" if ok else "FAIL"))
    results.append(ok)

    # #1c 有驗證碼欄位 + OCR 關閉 -> 直接按下一步(人工填答)
    ocr_calls.clear()
    btn = FakeNextButton()
    d = OrderDriver(next_button=btn, has_captcha=True)
    ret = bot.ticketplus_press_next_step(d, base_config(ocr_enable=False), None, None)
    ok = (ret is True) and (btn.click_count == 1) and (len(ocr_calls) == 0)
    print("[#1c captcha + ocr off -> direct press] ret=%s clicks=%d ocr=%d -> %s"
          % (ret, btn.click_count, len(ocr_calls), "PASS" if ok else "FAIL"))
    results.append(ok)
finally:
    bot.ticketplus_order_ocr = _real_ocr

print("----")
print("ALL PASS" if all(results) else "SOME FAILED")
real_time_mod.sleep(0)
sys.exit(0 if all(results) else 1)
