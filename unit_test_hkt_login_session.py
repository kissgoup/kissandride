#!/usr/bin/env python3
"""Unit tests for HKT date_keyword session match + login auto-fill helpers.

Uses fake elements (no browser) following unit_test_hkt_tier_select style.
Real DOM structure verified by probe_hkt_select.py (hkt_select_page.html):
  <div class="sessionListWrapper___gDIN1">
    <div class="sessionList___al29_ fouceStyle___Qr7dA">   <- fouceStyle = selected
      <div class="eventCaption___LUOTP"><span>2026年5月8日 (五) 晚上8時</span></div>
    </div>
  </div>
Login page DOM not yet dumped (session still valid); selectors are layered
fallbacks — see _hkt_find_login_inputs / _hkt_find_login_button.
"""
import unittest

import chrome_tixcraft as bot


class FakeRow:
    def __init__(self, text, css_class="sessionList___al29_"):
        self.text = text
        self._class = css_class

    def get_attribute(self, name):
        if name == "class":
            return self._class
        return None


class FakeWrapper:
    def __init__(self, rows):
        self._rows = rows

    def find_elements(self, by, selector):
        if selector == "./div":
            return self._rows
        return []


class FakeElement:
    def __init__(self, css_class="", text="", placeholder="", tag_type=None,
                 displayed=True):
        self._class = css_class
        self.text = text
        self._placeholder = placeholder
        self._type = tag_type
        self._displayed = displayed

    def get_attribute(self, name):
        if name == "class":
            return self._class
        if name == "placeholder":
            return self._placeholder
        if name == "type":
            return self._type
        if name == "value":
            return ""
        return None

    def is_displayed(self):
        return self._displayed


class FakeDriver:
    """Routes selector -> elements, mimicking the selectors the bot uses."""

    def __init__(self, wrappers=None, password_inputs=None, other_inputs=None,
                 regis_buttons=None, text_buttons=None, captcha_els=None):
        self._wrappers = wrappers or []
        self._password_inputs = password_inputs or []
        self._other_inputs = other_inputs or []
        self._regis_buttons = regis_buttons or []
        self._text_buttons = text_buttons or []
        self._captcha_els = captcha_els or []

    def find_elements(self, by, selector):
        if "sessionListWrapper_" in selector:
            return self._wrappers
        if "punish" in selector or "tmd" in selector or "baxia" in selector:
            return self._captcha_els
        if "input[type='password']" in selector:
            return self._password_inputs
        if "input:not" in selector:
            return self._other_inputs
        if "regis" in selector:
            return self._regis_buttons
        if selector.startswith("//button"):
            return self._text_buttons
        return []


def session_config(date_keyword="", date_enable=True):
    return {
        "advanced": {"verbose": False},
        "date_auto_select": {"enable": date_enable, "date_keyword": date_keyword},
    }


D1 = "2026年5月8日 (五) 晚上8時"
D2 = "2026年5月9日 (六) 晚上8時"


class TestHktParseDateKeywords(unittest.TestCase):
    def test_empty_returns_empty_list(self):
        self.assertEqual(bot.hkt_parse_date_keywords(session_config("")), [])

    def test_json_array_keyword(self):
        kws = bot.hkt_parse_date_keywords(session_config('"5月8日"'))
        self.assertEqual(kws, ["5月8日"])

    def test_invalid_json_returns_empty_list(self):
        self.assertEqual(bot.hkt_parse_date_keywords(session_config('"未閉合')), [])


class TestHktSelectSession(unittest.TestCase):
    def setUp(self):
        bot.hkt_dict = {"session_no_match_logged_time": 0.0}

    def test_no_wrapper_returns_none(self):
        driver = FakeDriver(wrappers=[])
        self.assertIsNone(bot.hkt_select_session(driver, session_config()))

    def test_date_disabled_returns_none(self):
        rows = [FakeRow(D1)]
        driver = FakeDriver(wrappers=[FakeWrapper(rows)])
        self.assertIsNone(
            bot.hkt_select_session(driver, session_config(date_enable=False)))

    def test_keyword_matches_only_target_session(self):
        rows = [FakeRow(D1), FakeRow(D2)]
        driver = FakeDriver(wrappers=[FakeWrapper(rows)])
        got = bot.hkt_select_session(driver, session_config('"5月8日"'))
        self.assertEqual(len(got), 1)
        self.assertIn("5月8日", got[0].text)

    def test_keyword_no_match_returns_empty_no_fallback(self):
        # 指定場次未命中時不可回退到其他場次（點錯場會浪費 addCart）。
        rows = [FakeRow(D1), FakeRow(D2)]
        driver = FakeDriver(wrappers=[FakeWrapper(rows)])
        got = bot.hkt_select_session(driver, session_config('"6月1日"'))
        self.assertEqual(got, [])

    def test_keyword_match_sold_out_returns_empty(self):
        sold_out = FakeRow(D1, "sessionList___x disableClass___y")
        rows = [sold_out, FakeRow(D2)]
        driver = FakeDriver(wrappers=[FakeWrapper(rows)])
        got = bot.hkt_select_session(driver, session_config('"5月8日"'))
        self.assertEqual(got, [])

    def test_no_keyword_returns_all_buyable(self):
        sold_out = FakeRow(D1, "sessionList___x disableClass___y")
        rows = [sold_out, FakeRow(D2)]
        driver = FakeDriver(wrappers=[FakeWrapper(rows)])
        got = bot.hkt_select_session(driver, session_config(""))
        self.assertEqual(len(got), 1)
        self.assertIn("5月9日", got[0].text)


class TestHktTargetSessionSelected(unittest.TestCase):
    def test_selected_row_has_fouce_style(self):
        rows = [FakeRow(D1, "sessionList___al29_ fouceStyle___Qr7dA")]
        self.assertTrue(bot.hkt_target_session_selected(rows))

    def test_no_fouce_style(self):
        rows = [FakeRow(D1), FakeRow(D2)]
        self.assertFalse(bot.hkt_target_session_selected(rows))


class TestHktLoginHelpers(unittest.TestCase):
    def test_captcha_dialog_present(self):
        driver = FakeDriver(captcha_els=[FakeElement()])
        self.assertTrue(bot.hkt_login_captcha_dialog_present(driver))
        self.assertFalse(bot.hkt_login_captcha_dialog_present(FakeDriver()))

    def test_find_login_inputs_by_placeholder(self):
        search = FakeElement(placeholder="請輸入節目、表演者")
        account = FakeElement(placeholder="請輸入電子郵件/手機號碼")
        driver = FakeDriver(
            password_inputs=[FakeElement(tag_type="password")],
            other_inputs=[search, account])
        acc, pwd = bot._hkt_find_login_inputs(driver)
        self.assertIsNotNone(acc)
        self.assertIn("電子郵件", acc._placeholder)
        self.assertIsNotNone(pwd)

    def test_find_login_inputs_fallback_first_non_search(self):
        misc = FakeElement(placeholder="請輸入會員編號")
        driver = FakeDriver(
            password_inputs=[FakeElement(tag_type="password")],
            other_inputs=[misc])
        acc, pwd = bot._hkt_find_login_inputs(driver)
        self.assertIs(acc, misc)
        self.assertIsNotNone(pwd)

    def test_find_login_inputs_needs_password(self):
        # 沒有密碼欄＝表單還沒渲染，整組回 None。
        driver = FakeDriver(other_inputs=[FakeElement(placeholder="電子郵件")])
        acc, pwd = bot._hkt_find_login_inputs(driver)
        self.assertIsNone(acc)
        self.assertIsNone(pwd)

    def test_find_login_button_by_regis_class(self):
        btn = FakeElement(css_class="bui-btn mz-button regis___xY9", text="登 入")
        driver = FakeDriver(regis_buttons=[btn])
        self.assertIs(bot._hkt_find_login_button(driver), btn)

    def test_find_login_button_by_text_fallback(self):
        btn = FakeElement(css_class="bui-btn mz-button", text="Login")
        driver = FakeDriver(text_buttons=[btn])
        self.assertIs(bot._hkt_find_login_button(driver), btn)

    def test_find_login_button_none(self):
        self.assertIsNone(bot._hkt_find_login_button(FakeDriver()))


if __name__ == "__main__":
    unittest.main()
