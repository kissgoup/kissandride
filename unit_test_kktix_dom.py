#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TDD failures discovered by crawl4ai + uc.Chrome probes on KKTIX 多場次活動頁.

Events crawled: weekendplanent.kktix.cc/events/6b8f2401
  └─ Session A: kktix.com/events/0cf6fd23/registrations/new 【13:00場】
  └─ Session B: kktix.com/events/6791ca87/registrations/new 【18:00場】

F1 (event-page next-btn): 新多場次頁結構是
    div.event-list > ul > li > div.content > a.btn-point
  沒有 .tickets 父層 -> kktix_events_press_next_button 的
  '.tickets > a.btn-point' 找到 0 個元素, bot 卡在活動頁.
F2 (reg next-btn click): btn.click() 可能被 wrapper 攔截
  (probe 印 element click intercepted) -> 需要 JS-click fallback.
"""
import unittest
from unittest.mock import MagicMock

import chrome_tixcraft as bot


class TestKKTIXEventPageNextButton(unittest.TestCase):
    """F1: '.tickets > a.btn-point' 在新多場次頁找不到元素.

    Desired: 找不到舊結構時退回 'a.btn-point'（活動頁唯一入口）並按下第一個。
    """

    def test_finds_btn_point_without_tickets_wrapper(self):
        """真實 YERIN event page: 只有 div.event-list 下的 a.btn-point.
        期望 function 仍能找到並點擊。目前 `.tickets > a.btn-point` 找到 0 -> 未點擊。
        """
        clicked = []
        driver = MagicMock()

        def fake_find_elements(by, sel):
            # 新 DOM: .tickets 子層查詢 0, 泛指 a.btn-point 有 2 個
            if sel == ".tickets > a.btn-point":
                return []
            if sel == "a.btn-point":
                btn = MagicMock()
                btn.is_enabled.return_value = True
                btn.click.side_effect = lambda: clicked.append("clicked")
                return [btn]
            return []

        driver.find_elements.side_effect = fake_find_elements
        ret = bot.kktix_events_press_next_button(driver)
        self.assertTrue(ret)
        self.assertEqual(clicked, ["clicked"])

    def test_legacy_tickets_selector_still_works(self):
        """回歸保護: 舊式 .tickets > a.btn-point 仍要能點擊。"""
        clicked = []
        driver = MagicMock()

        def fake_find_elements(by, sel):
            if sel == ".tickets > a.btn-point":
                btn = MagicMock()
                btn.is_enabled.return_value = True
                btn.click.side_effect = lambda: clicked.append("clicked")
                return [btn]
            return []

        driver.find_elements.side_effect = fake_find_elements
        ret = bot.kktix_events_press_next_button(driver)
        self.assertTrue(ret)
        self.assertEqual(clicked, ["clicked"])


class TestKKTIXNextBtnJSClick(unittest.TestCase):
    """F2: kktix_press_next_button 被攔截時要用 JS-click 補上。

    probe 證據: Element click intercepted: Other element would receive the click:
    <div class="form-actions plain align-center register-new-next-button-area">...
    """

    def test_click_intercepted_falls_back_to_js_click(self):
        """btn.click() 被攔截 -> execute_script('arguments[0].click()') 必須被呼叫。
        目前版本沒有 JS fallback -> execute_script 只收到 focus -> test fail。
        """
        btn = MagicMock()
        btn.click.side_effect = Exception("element click intercepted")
        js_calls = []
        driver = MagicMock()
        driver.find_elements.return_value = [btn]
        driver.execute_script.side_effect = lambda js, el: js_calls.append(js)

        ret = bot.kktix_press_next_button(driver)

        self.assertTrue(ret)
        # JS click fallback 被執行
        self.assertTrue(any("arguments[0].click()" in js for js in js_calls),
                        "expected JS click fallback, got: %s" % js_calls)

    def test_click_success_no_js_click_needed(self):
        """正常可點擊時不額外跑 JS click。"""
        btn = MagicMock()
        clicked = []
        btn.click.side_effect = lambda: clicked.append("clicked")
        driver = MagicMock()
        driver.find_elements.return_value = [btn]
        js_calls = []
        driver.execute_script.side_effect = lambda js, el: js_calls.append(js)

        ret = bot.kktix_press_next_button(driver)
        self.assertTrue(ret)
        self.assertEqual(clicked, ["clicked"])
        self.assertFalse(any("arguments[0].click()" in js for js in js_calls))


class TestKKTIXMainNoCrashOnEmpty(unittest.TestCase):
    """防禦: kktix_events_press_next_button 找不到按鈕時不該丟例外。"""

    def test_no_btn_point_returns_false_gracefully(self):
        driver = MagicMock()
        driver.find_elements.return_value = []
        try:
            ret = bot.kktix_events_press_next_button(driver)
        except Exception:
            self.fail("kktix_events_press_next_button should not raise")
        self.assertFalse(ret)


class TestKKTIXAgreeTickGatesNext(unittest.TestCase):
    """root cause (reg_new_plain.js RegistrationsNewCtrl):

    couldNextStep() = conditions.agreeTerm && ticketChosen() && hasNoEmptyInputCode()
                      && (!displayKtxCaptcha() || ...)
    """
    def _make_agree_checkbox(self, clicked):
        agree = MagicMock()
        agree.is_enabled.return_value = True
        agree.is_selected.return_value = False
        agree.click.side_effect = lambda: clicked.append("tick")
        return agree

    def test_press_next_ticks_agree_checkbox(self):
        """新 seat-selection DOM: next 按鈕被 couldNextStep() gate, 需先勾
        #person_agree_terms. kktix_press_next_button 按下前要 tick agree。"""
        agree_clicked = []
        agree = self._make_agree_checkbox(agree_clicked)
        btn = MagicMock()
        btn.is_enabled.return_value = True
        clicked = []
        btn.click.side_effect = lambda: clicked.append("click")

        driver = MagicMock()
        driver.find_elements.return_value = [btn]
        driver.find_element.side_effect = lambda by, sel: (
            agree if sel == "#person_agree_terms" else (_ for _ in ()).throw(Exception("no such element"))
        )
        js_calls = []
        driver.execute_script.side_effect = lambda js, el=None: js_calls.append(js)

        ret = bot.kktix_press_next_button(driver)
        self.assertTrue(ret)
        self.assertEqual(agree_clicked, ["tick"],
                         "agree checkbox must be ticked before next click; "
                         "couldNextStep() returns false otherwise -> button stays disabled")

    def test_no_agree_checkbox_press_still_works(self):
        """舊式流程沒有第一頁 agree checkbox 時, 不能 raise、照樣能按 next。"""
        btn = MagicMock()
        btn.is_enabled.return_value = True
        clicked = []
        btn.click.side_effect = lambda: clicked.append("click")
        driver = MagicMock()
        driver.find_elements.return_value = [btn]
        driver.find_element.side_effect = lambda by, sel: (_ for _ in ()).throw(Exception("no such element"))
        js_calls = []
        driver.execute_script.side_effect = lambda js, el=None: js_calls.append(js)

        ret = bot.kktix_press_next_button(driver)
        self.assertTrue(ret)
        self.assertEqual(clicked, ["click"])

    def test_agree_tick_idempotent_when_already_checked(self):
        """已勾選狀態不能重複點 (force_check 應早退)。"""
        agree = MagicMock()
        agree.is_enabled.return_value = True
        agree.is_selected.return_value = True   # already checked
        agree.click.side_effect = AssertionError("should not re-click")
        btn = MagicMock()
        btn.is_enabled.return_value = True
        btn.click.return_value = None
        driver = MagicMock()
        driver.find_elements.return_value = [btn]
        driver.find_element.side_effect = lambda by, sel: (
            agree if sel == "#person_agree_terms" else (_ for _ in ()).throw(Exception("no such element"))
        )
        ret = bot.kktix_press_next_button(driver)
        self.assertTrue(ret)


if __name__ == "__main__":
    unittest.main()
