#!/usr/bin/env python3
"""Unit tests for hkt_get_target_tier / hkt_parse_price_keywords.

Uses fake elements (no browser) following unit_test_tixcraft_area_select style.
Real DOM structure verified by probe_hkt_select_dom.py / probe_hkt_tier_click.py
(hkt_select_page.html, hkt_tier_selected.html):
  <div class="levelItem___rPZ55 disableClass___BDFqG"><span class="ticketText___...">VIP 門票 (HK$ 1799.00)<div class="sign___...">暫無可售</div></span></div>
  <div class="levelItem___rPZ55"><span class="ticketText___...">A/標準門票 (HK$ 1399.00)</span></div>
  <div class="levelItem___rPZ55"><span class="ticketText___...">B/標準門票 (HK$ 999.00)</span></div>
"""
import time
import unittest

import chrome_tixcraft as bot


class FakeTierRow:
    def __init__(self, text, css_class="levelItem___rPZ55"):
        self.text = text
        self._class = css_class

    def get_attribute(self, name):
        if name == "class":
            return self._class
        return None


class FakeDriver:
    def __init__(self, rows):
        self.rows = rows

    def find_elements(self, by, selector):
        if "levelItem_" in selector:
            return self.rows
        return []


def make_config(keyword, ticket_number=2):
    return {
        "advanced": {"verbose": False},
        "area_auto_select": {"mode": "random", "area_keyword": keyword},
        "ticket_number": ticket_number,
    }


VIP_ROW = FakeTierRow(
    "VIP 門票 (HK$ 1799.00)\n暫無可售",
    "levelItem___rPZ55 disableClass___BDFqG",
)
A_ROW = FakeTierRow("A/標準門票  (HK$ 1399.00)")
B_ROW = FakeTierRow("B/標準門票  (HK$ 999.00)")


class TestHktParsePriceKeywords(unittest.TestCase):
    def test_empty_keyword_returns_empty_list(self):
        self.assertEqual(bot.hkt_parse_price_keywords(make_config("")), [])

    def test_json_array_keywords(self):
        # settings 欄位格式：JSON 轉義字串（同 tixcraft）。
        cfg = make_config('"A/標準門票","VIP"')
        kws = bot.hkt_parse_price_keywords(cfg)
        self.assertEqual(len(kws), 2)
        self.assertIn("a/標準門票", kws[0].lower() or kws[0])
        self.assertTrue(any("vip" in k.lower() for k in kws))

    def test_invalid_json_returns_empty_list(self):
        self.assertEqual(bot.hkt_parse_price_keywords(make_config('"未閉合')), [])


class TestHktGetTargetTier(unittest.TestCase):
    def test_sold_out_rows_excluded(self):
        driver = FakeDriver([VIP_ROW])
        target = bot.hkt_get_target_tier(driver, make_config(""))
        self.assertIsNone(target)

    def test_first_buyable_without_keyword(self):
        driver = FakeDriver([VIP_ROW, A_ROW, B_ROW])
        target = bot.hkt_get_target_tier(driver, make_config(""))
        self.assertIsNotNone(target)
        self.assertIn("1399", target[1])

    def test_keyword_match(self):
        driver = FakeDriver([VIP_ROW, A_ROW, B_ROW])
        target = bot.hkt_get_target_tier(driver, make_config('"B/標準門票"'))
        self.assertIsNotNone(target)
        self.assertIn("999", target[1])

    def test_keyword_all_tokens_must_match(self):
        # AND rule: 「標準 999」命中 B；「標準 1399」命中 A；「VIP 999」無人命中。
        driver = FakeDriver([VIP_ROW, A_ROW, B_ROW])
        t1 = bot.hkt_get_target_tier(driver, make_config('"標準 999"'))
        self.assertIn("999", t1[1])
        t2 = bot.hkt_get_target_tier(driver, make_config('"標準 1399"'))
        self.assertIn("1399", t2[1])
        t3 = bot.hkt_get_target_tier(driver, make_config('"VIP 999"'))
        self.assertIsNone(t3)

    def test_no_match_returns_none(self):
        driver = FakeDriver([VIP_ROW, A_ROW, B_ROW])
        target = bot.hkt_get_target_tier(driver, make_config('"不存在"'))
        self.assertIsNone(target)

    def test_no_rows_returns_none(self):
        driver = FakeDriver([])
        target = bot.hkt_get_target_tier(driver, make_config(""))
        self.assertIsNone(target)

    def test_disable_class_row_even_without_soldout_text(self):
        # 防禦性：class 帶 disableClass 但文字沒有「暫無可售」也要排除。
        weird = FakeTierRow("C/標準門票 (HK$ 599.00)", "levelItem___x disableClass___y")
        driver = FakeDriver([weird])
        target = bot.hkt_get_target_tier(driver, make_config(""))
        self.assertIsNone(target)


class ClickableEl:
    def __init__(self, text="", css_class="", displayed=True, spans=None,
                 buy_holder=None):
        self.text = text
        self._class = css_class
        self._displayed = displayed
        self._spans = list(spans or [])
        self.buy_holder = buy_holder
        self.native_clicks = 0

    def get_attribute(self, name):
        if name == "class":
            return self._class
        return None

    def is_displayed(self):
        return self._displayed

    def is_enabled(self):
        return True

    def click(self):
        self.native_clicks += 1

    def find_elements(self, by, selector):
        return list(self._spans)

    def find_element(self, by, selector):
        if "buyNum_" in selector:
            if self.buy_holder is None:
                self.buy_holder = ClickableEl()
            return self.buy_holder
        raise Exception("unexpected selector: " + selector)


class QtyFlowDriver:
    """Routes the selectors hkt_ticket_auto_select uses, tracking clicks."""

    def __init__(self, tier_rows, num_list_text=None, qty="", total="0.00",
                 next_btn=None):
        self.tier_rows = tier_rows
        self.num_list_text = num_list_text
        self.qty_text = qty
        self.total_text = total
        self.next_btn = next_btn
        self.js_click_count = 0

    def find_elements(self, by, selector):
        if "sessionListWrapper_" in selector:
            return []
        if "levelItem_" in selector:
            return self.tier_rows
        if "numList_" in selector:
            if self.num_list_text is None:
                return []
            return [ClickableEl(text=self.num_list_text)]
        if selector.startswith("//button"):
            return [self.next_btn] if self.next_btn is not None else []
        return []

    def find_element(self, by, selector):
        if "buyNum_" in selector:
            return ClickableEl()  # holder; spans come from find_elements below
        if "totalWrapper_" in selector:
            return ClickableEl(text=self.total_text)
        raise Exception("unexpected selector: " + selector)

    def execute_script(self, script, *args):
        self.js_click_count += 1


class QtySpanDriver(QtyFlowDriver):
    """Rendered numList element carries a buyNum holder with spans:
    [minus, qty, plus]."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.buy_num_holder = ClickableEl(spans=[
            ClickableEl(),                     # [0] minus (icon-jian)
            ClickableEl(text=self.qty_text),   # [1] 顯示張數
            ClickableEl(),                     # [2] plus (icon-jia)
        ])

    def find_elements(self, by, selector):
        if "numList_" in selector:
            if self.num_list_text is None:
                return []
            el = ClickableEl(text=self.num_list_text,
                             buy_holder=self.buy_num_holder)
            return [el]
        return super().find_elements(by, selector)


def make_qty_config(ticket_number=2):
    return {
        "advanced": {"verbose": False},
        "area_auto_select": {"enable": True, "area_keyword": '"A/標準門票"'},
        "date_auto_select": {"enable": True, "date_keyword": ""},
        "ticket_number": ticket_number,
    }


def make_hkt_dict():
    return {
        "is_login_hint_shown": False, "is_captcha_hint_shown": False,
        "is_login_stuck_hint": False, "login_click_time": 0.0,
        "login_submit_count": 0, "is_popup_confirm": False,
        "next_btn_pressed_time": 0.0, "seat_btn_pressed_time": 0.0,
        "session_cursor": 0, "session_click_time": 0.0,
        "session_no_match_logged_time": 0.0, "tier_click_time": 0.0,
        "tier_clicked_text": "", "tier_click_count": 0,
        "qty_click_time": 0.0, "qty_last_seen": 0,
        "qty_stall_count": 0, "qty_stall_hint_shown": False,
    }


class TestHktQuantityGate(unittest.TestCase):
    def setUp(self):
        bot.hkt_dict = make_hkt_dict()

    def test_qty_displayed_and_matching_before_next_step(self):
        # 購買數量已顯示、張數=設定：才按下一步。
        tier = ClickableEl(text="A/標準門票  (HK$ 1399.00)",
                           css_class="levelItem___rPZ55")
        nl = "A/標準門票  (HK$ 1399.00)\n2"
        driver = QtySpanDriver([tier], num_list_text=nl, qty="2",
                               total="2798.00", next_btn=ClickableEl())
        bot.hkt_ticket_auto_select(driver, "", make_qty_config())
        self.assertEqual(driver.next_btn.native_clicks, 1)

    def test_qty_below_setting_blocks_next_step(self):
        # 購買數量顯示 1、設定 2：只點 +，不可按下一步。
        tier = ClickableEl(text="A/標準門票  (HK$ 1399.00)",
                           css_class="levelItem___rPZ55")
        nl = "A/標準門票  (HK$ 1399.00)\n1"
        driver = QtySpanDriver([tier], num_list_text=nl, qty="1",
                               total="1399.00", next_btn=ClickableEl())
        bot.hkt_ticket_auto_select(driver, "", make_qty_config())
        self.assertEqual(driver.next_btn.native_clicks, 0)
        self.assertEqual(driver.js_click_count, 1)  # + 被點一次

    def test_qty_not_displayed_waits_without_reclick(self):
        # 購買數量還沒渲染：等（不重點票檔、不按下一步）。
        tier = ClickableEl(text="A/標準門票  (HK$ 1399.00)",
                           css_class="levelItem___rPZ55")
        driver = QtySpanDriver([tier], num_list_text=None,
                               next_btn=ClickableEl())
        bot.hkt_ticket_auto_select(driver, "", make_qty_config())
        self.assertEqual(tier.native_clicks, 1)  # 第一次會點票檔
        bot.hkt_ticket_auto_select(driver, "", make_qty_config())
        self.assertEqual(tier.native_clicks, 1)  # 2 秒內不重點
        self.assertEqual(driver.next_btn.native_clicks, 0)

    def test_total_zero_blocks_next_step(self):
        # 張數對了但總額還是 0（價格未按張數重算）：不按下一步。
        tier = ClickableEl(text="A/標準門票  (HK$ 1399.00)",
                           css_class="levelItem___rPZ55")
        nl = "A/標準門票  (HK$ 1399.00)\n2"
        driver = QtySpanDriver([tier], num_list_text=nl, qty="2",
                               total="0.00", next_btn=ClickableEl())
        bot.hkt_ticket_auto_select(driver, "", make_qty_config())
        self.assertEqual(driver.next_btn.native_clicks, 0)

    def test_qty_stall_stops_submitting(self):
        # + 點了張數不動（每單限購）：停止自動送出，不按下一步。
        tier = ClickableEl(text="A/標準門票  (HK$ 1399.00)",
                           css_class="levelItem___rPZ55")
        nl = "A/標準門票  (HK$ 1399.00)\n1"
        driver = QtySpanDriver([tier], num_list_text=nl, qty="1",
                               total="1399.00", next_btn=ClickableEl())
        bot.hkt_dict["qty_stall_count"] = 8  # 已達無效點擊上限
        bot.hkt_ticket_auto_select(driver, "", make_qty_config())
        self.assertEqual(driver.js_click_count, 0)  # 不再點 +
        self.assertEqual(driver.next_btn.native_clicks, 0)
        self.assertTrue(bot.hkt_dict["qty_stall_hint_shown"])

    def test_qty_recent_plus_click_waits_for_redraw(self):
        # 0.6 秒內剛點過 +：等 React 重繪，不重複點。
        tier = ClickableEl(text="A/標準門票  (HK$ 1399.00)",
                           css_class="levelItem___rPZ55")
        nl = "A/標準門票  (HK$ 1399.00)\n1"
        driver = QtySpanDriver([tier], num_list_text=nl, qty="1",
                               next_btn=ClickableEl())
        bot.hkt_dict["qty_last_seen"] = 1
        bot.hkt_dict["qty_click_time"] = time.time()
        bot.hkt_ticket_auto_select(driver, "", make_qty_config())
        self.assertEqual(driver.js_click_count, 0)


class TestHktTierNameKey(unittest.TestCase):
    def test_name_is_prefix_before_price(self):
        key = bot.hkt_tier_name_key("A/標準門票  (HK$ 1399.00)")
        self.assertEqual(key, "a/標準門票")

    def test_row_with_limit_hint_still_yields_name(self):
        # 票檔列附加「限購」提示時，名字前綴不受影響。
        key = bot.hkt_tier_name_key("A/標準門票 (HK$ 1399.00) 每筆訂單限購4張")
        self.assertEqual(key, "a/標準門票")

    def test_name_key_selected_check_fallback(self):
        # 整段文字比不過（票檔列有附加文字）時，票名前綴要能判定已選中。
        tier_text = "A/標準門票 (HK$ 1399.00) 每筆訂單限購4張"
        tier_full = bot.util.format_keyword_string(tier_text)
        tier_key = bot.hkt_tier_name_key(tier_text)
        nl_text = bot.util.format_keyword_string("A/標準門票 (HK$ 1399.00)\n1")
        self.assertFalse(nl_text.startswith(tier_full))
        self.assertTrue(nl_text.startswith(tier_key))


class NumListFakeDriver:
    def __init__(self, labels):
        self._labels = labels

    def find_elements(self, by, selector):
        if "numList_" in selector:
            return [ClickableEl(text=t) for t in self._labels]
        return []


def kw_config(keyword):
    return {"area_auto_select": {"area_keyword": keyword}}


class TestHktRenderedNumList(unittest.TestCase):
    LABEL = "B/標準門票 (企位)\n0"
    ADDON = "藝人優先購票 (HK$ 1499.00)\n0"

    def test_no_keyword_accepts_any_rendered(self):
        got = bot.hkt_rendered_num_list(
            NumListFakeDriver([self.ADDON]), kw_config(""))
        self.assertIsNotNone(got)

    def test_keyword_match_accepts(self):
        got = bot.hkt_rendered_num_list(
            NumListFakeDriver([self.ADDON]), kw_config('"藝人優先"'))
        self.assertIsNotNone(got)

    def test_keyword_mismatch_clicked_prefix_accepts(self):
        # 點了 B/標準門票，面板 label 是同名票（價格式不同）→ 票名前綴兜底。
        got = bot.hkt_rendered_num_list(
            NumListFakeDriver(["B/標準門票(企位) (HK$1499.00)\n0"]),
            kw_config('"A/標準門票"'), "B/標準門票 (企位) (HK$ 1499.00)")
        self.assertIsNotNone(got)

    def test_keyword_and_clicked_both_mismatch_returns_none(self):
        got = bot.hkt_rendered_num_list(
            NumListFakeDriver([self.ADDON]), kw_config('"A/標準門票"'),
            "B/標準門票 (企位) (HK$ 1499.00)")
        self.assertIsNone(got)

    def test_no_numlist_returns_none(self):
        got = bot.hkt_rendered_num_list(NumListFakeDriver([]), kw_config(""))
        self.assertIsNone(got)


if __name__ == "__main__":
    unittest.main()
