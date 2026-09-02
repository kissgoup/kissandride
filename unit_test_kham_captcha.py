#!/usr/bin/env python3
"""Unit tests for kham_keyin_captcha_code (kham 驗證碼填寫，第 3 步).

真實 step-3 DOM（crawl4ai 爬 UTK0205_.aspx 驗證）:
    <input name="ctl00$ContentPlaceHolder1$CHK" type="text" maxlength="4"
           id="CHK" placeholder="驗證碼">

實測 bug（uc.Chrome 開 kham step-3 頁）:
  - send_keys() 靜默失效：鍵盤事件完全進不了頁面（document 層 keydown/input
    事件都偵測不到），不拋例外，value 保持空。
  - JS 直接設值 + dispatch input/change 事件有效且留存。

回歸測試模擬 send_keys 靜默失敗，斷言 bot 會回退用 JS 設值把驗證碼填進去。
"""
import unittest

from selenium.common.exceptions import NoSuchElementException

import chrome_tixcraft as bot


class FakeInput:
    """模擬 #CHK input；send_keys 靜默 no-op（複現 uc.Chrome 的 kham bug）。"""

    def __init__(self, el_id="CHK"):
        self.el_id = el_id
        self.value = ""

    def get_attribute(self, name):
        if name == "value":
            return self.value
        if name == "id":
            return self.el_id
        return None

    def clear(self):
        self.value = ""

    def send_keys(self, keys):
        # 複現 kham step-3 的 uc.Chrome bug：不拋例外、value 不變。
        pass

    def set_value(self, v):
        self.value = v


class FakeDriver:
    """find_element 對任何 captcha selector 回傳 FakeInput；
    execute_script 模擬 JS 回退（el.value = v; dispatch events）。"""

    def __init__(self, chk_input):
        self.chk = chk_input
        self.scripts_run = []

    def find_element(self, by, selector):
        if "CHK" in selector or "驗證碼" in selector or 'maxlength="4"' in selector:
            return self.chk
        raise NoSuchElementException("no such element: %s" % selector)

    def execute_script(self, js, *args):
        self.scripts_run.append(js)
        if len(args) >= 2:
            el, val = args[0], args[1]
            el.set_value(val)
        return None


class TestKhamKeyinCaptchaCode(unittest.TestCase):

    def test_fills_captcha_when_send_keys_silently_fails(self):
        """bug #2: send_keys 靜默失敗時，仍應透過 JS 回退把驗證碼填入 #CHK。"""
        chk = FakeInput()
        driver = FakeDriver(chk)
        bot.kham_keyin_captcha_code(driver, answer="A1B2", auto_submit=False)
        self.assertEqual(chk.value, "A1B2", "驗證碼應被填入 #CHK")
        self.assertTrue(driver.scripts_run, "應執行 JS 回退填值")

    def test_clears_field_when_no_answer(self):
        """answer 為空時應清空驗證碼欄位（不填入）。"""
        chk = FakeInput()
        chk.value = "OLD"
        driver = FakeDriver(chk)
        bot.kham_keyin_captcha_code(driver, answer="", auto_submit=False)
        self.assertEqual(chk.value, "")


if __name__ == "__main__":
    unittest.main()
