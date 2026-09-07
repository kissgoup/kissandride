#!/usr/bin/env python3
#encoding=utf-8
# 單元級驗證: ticketplus /order/ code 表單 (ticketplus.code_fields) 自動填入決策。
#   P1 _ticketplus_code_fields 防呆讀取(None/空/缺區塊/非 list/壞 row/正常)
#   P2 _ticketplus_entry_matches 中文字命中/空 ctx/大小寫/無 match
#   F1 中信卡前六碼(placeholder+label)填入 123456
#   F2 預購碼任意長度值整串填入(不限制字元數)
#   F3 僅 placeholder(無 .label) 也能命中
#   F4 冪等: 已填相同值不再送、不補事件
#   F5 無候選輸入框 -> False
#   F6 舊 settings 無 ticketplus 區塊 -> False、不碰輸入框
#   F7 驗證碼框不誤填(placeholder=請輸入驗證碼)
#   F8 JS 常數: 排除驗證碼、不排除 .exclusive-code(相容未知 wrapper)
#   F9 一頁多欄位: 每筆 entry 各填各的框
#   A1 ticketplus_order_apply_code_gate: 有填->True; 無設定(feature off)->False 零行為
import sys
import time as real_time_mod

import chrome_tixcraft as bot


class FakeElement:
    def __init__(self, placeholder="", ctx=None, current_value=""):
        self.placeholder = placeholder
        self.ctx = ctx if ctx is not None else placeholder   # 模擬 CTX_JS 回傳
        self.value = current_value
        self.sent = None
        self.cleared = False
        self.sync_called = 0

    def get_attribute(self, name):
        return {"placeholder": self.placeholder, "value": self.value}.get(name)

    def clear(self):
        self.cleared = True
        self.value = ""

    def send_keys(self, text):
        self.sent = text
        self.value = self.value + text


class FakeCodeDriver:
    def __init__(self, candidates):
        self.candidates = list(candidates)
        self.executed = []

    def execute_script(self, code, *args):
        self.executed.append(code)
        if code == bot.CONST_TICKETPLUS_CODE_FIELD_COLLECT_JS:
            return list(self.candidates)
        if code == bot.CONST_TICKETPLUS_CODE_FIELD_CTX_JS:
            el = args[0]
            ctx = getattr(el, "ctx", None)
            if ctx is None:
                try:
                    ctx = el.get_attribute("placeholder") or ""
                except Exception:
                    ctx = ""
            return ctx
        if code == bot.CONST_TICKETPLUS_CODE_FIELD_SYNC_JS:
            if hasattr(args[0], "sync_called"):
                args[0].sync_called += 1
            return None
        return None

    def find_elements(self, by, css):
        # apply_code_gate 的 agree 掃描: 沒有 checkbox -> 空 list(安全 no-op)
        return []


def code_config(fields):
    return {"advanced": {"verbose": False}, "ticketplus": {"code_fields": list(fields)}}


CTBC_CTX = "請輸入中國信託信用卡或簽帳金融卡 卡號前六碼 中國信託信用卡或簽帳金融卡 卡號前六碼"


results = []

# P1 _ticketplus_code_fields 防呆讀取
ok = bot._ticketplus_code_fields(None) == []
print("[P1 None config] -> %s" % ("PASS" if ok else "FAIL")); results.append(ok)

ok = bot._ticketplus_code_fields({}) == []
print("[P1 empty config] -> %s" % ("PASS" if ok else "FAIL")); results.append(ok)

ok = bot._ticketplus_code_fields({"ticketplus": {}}) == []
print("[P1 no code_fields key] -> %s" % ("PASS" if ok else "FAIL")); results.append(ok)

ok = bot._ticketplus_code_fields({"ticketplus": {"code_fields": "not-a-list"}}) == []
print("[P1 code_fields not list] -> %s" % ("PASS" if ok else "FAIL")); results.append(ok)

valid_row = {"match": "中國信託", "value": "123456"}
ok = bot._ticketplus_code_fields({"ticketplus": {"code_fields": [valid_row]}}) == [valid_row]
print("[P1 valid row kept] -> %s" % ("PASS" if ok else "FAIL")); results.append(ok)

bad_rows = [
    {"value": "no-match"},
    {"match": "中國信託"},          # 無 value
    {"match": "", "value": "x"},   # match 空字串
    {"match": "a", "value": 3},    # value 非 str
    "plain-string",                 # 非 dict
    None,
]
ok = bot._ticketplus_code_fields({"ticketplus": {"code_fields": bad_rows}}) == []
print("[P1 bad rows filtered] -> %s" % ("PASS" if ok else "FAIL")); results.append(ok)

# P2 _ticketplus_entry_matches
ok = bot._ticketplus_entry_matches(CTBC_CTX, {"match": "中國信託", "value": "123456"}) is True
print("[P2 chinese substring hit] -> %s" % ("PASS" if ok else "FAIL")); results.append(ok)

ok = bot._ticketplus_entry_matches(None, {"match": "中國信託", "value": "123456"}) is False
print("[P2 None ctx] -> %s" % ("PASS" if ok else "FAIL")); results.append(ok)

ok = bot._ticketplus_entry_matches("abc", {"match": "ABC", "value": "1"}) is False
print("[P2 case sensitive miss] -> %s" % ("PASS" if ok else "FAIL")); results.append(ok)

ok = bot._ticketplus_entry_matches("abc", {}) is False
print("[P2 entry without match] -> %s" % ("PASS" if ok else "FAIL")); results.append(ok)

# F1 中信卡前六碼: placeholder + label 都含「中國信託」-> 填 123456
el = FakeElement(placeholder="中國信託信用卡或簽帳金融卡 卡號前六碼", ctx=CTBC_CTX, current_value="")
driver = FakeCodeDriver([el])
ret = bot.ticketplus_fill_code_fields_by_settings(
    driver, code_config([{"match": "中國信託", "value": "123456"}]))
ok = ret is True and el.value == "123456" and el.sent == "123456" and el.sync_called == 1
print("[F1 CTBC card filled] -> %s" % ("PASS" if ok else "FAIL")); results.append(ok)

# F2 預購碼任意長度值整串填入(不限制字元數)
el2 = FakeElement(placeholder="請輸入預購碼", ctx="請輸入預購碼", current_value="")
long_code = "ABC123456789XYZ"
driver2 = FakeCodeDriver([el2])
ret = bot.ticketplus_fill_code_fields_by_settings(
    driver2, code_config([{"match": "預購碼", "value": long_code}]))
ok = ret is True and el2.value == long_code
print("[F2 presale code any length] -> %s" % ("PASS" if ok else "FAIL")); results.append(ok)

# F3 僅 placeholder(無 .label) 也能命中
el3 = FakeElement(placeholder="中國信託信用卡或簽帳金融卡 卡號前六碼", ctx=None, current_value="")
driver3 = FakeCodeDriver([el3])
ret = bot.ticketplus_fill_code_fields_by_settings(
    driver3, code_config([{"match": "卡號前六碼", "value": "432143"}]))
ok = ret is True and el3.value == "432143"
print("[F3 placeholder-only matched] -> %s" % ("PASS" if ok else "FAIL")); results.append(ok)

# F4 冪等: 已填相同值 -> False、不再 send、不補事件
el4 = FakeElement(placeholder="請輸入預購碼", ctx="請輸入預購碼", current_value="UNQ5F7")
driver4 = FakeCodeDriver([el4])
ret = bot.ticketplus_fill_code_fields_by_settings(
    driver4, code_config([{"match": "預購碼", "value": "UNQ5F7"}]))
ok = ret is False and el4.sent is None and el4.sync_called == 0
print("[F4 idempotent same value] -> %s" % ("PASS" if ok else "FAIL")); results.append(ok)

# F5 無候選輸入框 -> False
driver5 = FakeCodeDriver([])
ret = bot.ticketplus_fill_code_fields_by_settings(
    driver5, code_config([{"match": "預購碼", "value": "ABC"}]))
ok = ret is False
print("[F5 no candidate input] -> %s" % ("PASS" if ok else "FAIL")); results.append(ok)

# F6 舊 settings 無 ticketplus 區塊 -> False、不碰輸入框
el6 = FakeElement(placeholder="請輸入預購碼", ctx="請輸入預購碼", current_value="")
driver6 = FakeCodeDriver([el6])
ret = bot.ticketplus_fill_code_fields_by_settings(driver6, {"advanced": {"verbose": False}})
ok = ret is False and el6.sent is None
print("[F6 old settings no ticketplus block] -> %s" % ("PASS" if ok else "FAIL")); results.append(ok)

# F7 驗證碼框不誤填
el7 = FakeElement(placeholder=bot.CONST_TICKETPLUS_OCR_CAPTCHA_PLACEHOLDER,
                  ctx=bot.CONST_TICKETPLUS_OCR_CAPTCHA_PLACEHOLDER, current_value="")
driver7 = FakeCodeDriver([el7])
ret = bot.ticketplus_fill_code_fields_by_settings(
    driver7, code_config([{"match": "驗證碼", "value": "9999"}]))
ok = ret is False and el7.sent is None
print("[F7 captcha input skipped] -> %s" % ("PASS" if ok else "FAIL")); results.append(ok)

# F8 JS 常數設計: 收集端排除驗證碼; 刻意不排除 .exclusive-code(未知 wrapper 相容)
ok = bot.CONST_TICKETPLUS_OCR_CAPTCHA_PLACEHOLDER in bot.CONST_TICKETPLUS_CODE_FIELD_COLLECT_JS
print("[F8 JS excludes captcha placeholder] -> %s" % ("PASS" if ok else "FAIL")); results.append(ok)

ok = (".exclusive-code" not in bot.CONST_TICKETPLUS_CODE_FIELD_COLLECT_JS
      and ".exclusive-code" not in bot.CONST_TICKETPLUS_CODE_FIELD_CTX_JS)
print("[F8 JS keeps exclusive-code subtree reachable] -> %s" % ("PASS" if ok else "FAIL")); results.append(ok)

# F9 一頁多欄位: 兩筆 entry 各填各的框
elA = FakeElement(placeholder="中國信託信用卡或簽帳金融卡 卡號前六碼", ctx=CTBC_CTX, current_value="")
elB = FakeElement(placeholder="請輸入預購碼", ctx="請輸入預購碼", current_value="")
driver9 = FakeCodeDriver([elA, elB])
ret = bot.ticketplus_fill_code_fields_by_settings(driver9, code_config([
    {"match": "中國信託", "value": "123456"},
    {"match": "預購碼", "value": "PROMO9"},
]))
ok = ret is True and elA.value == "123456" and elB.value == "PROMO9"
print("[F9 multi-field page] -> %s" % ("PASS" if ok else "FAIL")); results.append(ok)

# A1 ticketplus_order_apply_code_gate: 有設定且填了 -> True
elA1 = FakeElement(placeholder="中國信託信用卡或簽帳金融卡 卡號前六碼", ctx=CTBC_CTX, current_value="")
driverA1 = FakeCodeDriver([elA1])
ret = bot.ticketplus_order_apply_code_gate(
    driverA1, code_config([{"match": "中國信託", "value": "123456"}]))
ok = ret is True and elA1.value == "123456"
print("[A1 apply gate fills] -> %s" % ("PASS" if ok else "FAIL")); results.append(ok)

# A2 apply gate feature off: 無 code_fields -> False、輸入框不被碰(含 agree 也不跑)
elA2 = FakeElement(placeholder="請輸入預購碼", ctx="請輸入預購碼", current_value="")
driverA2 = FakeCodeDriver([elA2])
ret = bot.ticketplus_order_apply_code_gate(driverA2, {"advanced": {"verbose": False}})
ok = ret is False and elA2.sent is None
print("[A2 apply gate feature off no-op] -> %s" % ("PASS" if ok else "FAIL")); results.append(ok)

print("----")
print("ALL PASS" if all(results) else "SOME FAILED")
real_time_mod.sleep(0)
sys.exit(0 if all(results) else 1)
