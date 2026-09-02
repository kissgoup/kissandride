#!/usr/bin/env python3
"""Unit tests for kham_area_auto_select (kham 區域選擇，第 2 步).

Uses fake driver/row objects (no browser), following the tixcraft unit test
style. The fake row HTML is taken from the real crawled page (kham_step2.html):

  <tr class="status_tr" rel="a20 a21 a22" id="P1D9ZT7S" style="cursor: pointer;">
      <td><div class="colorblock" style="background-color:#DD94CD"></div></td>
      <td data-title="票區：">平面特1區4680元</td>
      <td data-title="票價：">4,680</td>
      <td data-title="空位：">4</td>
  </tr>

Verified behaviour (against the real page):
  - 空位 (remaining count) is the LAST <td>; rows with fewer than
    ticket_number remaining are skipped (e.g. 空位 1 while buying 2).
  - 熱賣中 rows are kept (not a digit, so the count filter is skipped).
  - rows with '售完' text are excluded (safety net; the real CSS selector
    `[class='status_tr']` already excludes `class="status_tr Soldout"` rows).
  - area_keyword_item filters which area row is clicked.
"""
import unittest

import chrome_tixcraft as bot


class FakeRow:
    """Fake <tr>; innerHTML like a real kham step-2 area row."""

    def __init__(self, inner_html, enabled=True):
        self.html = inner_html
        self.enabled = enabled
        self.clicked = False

    def get_attribute(self, name):
        if name == "innerHTML":
            return self.html
        return None

    def is_enabled(self):
        return self.enabled

    def click(self):
        self.clicked = True


class FakeDriver:
    def __init__(self, rows):
        self.rows = rows

    def find_elements(self, by, selector):
        return self.rows


# ---- real row HTML from kham_step2.html ----------------------------------

def area_row(name, price, remaining_text, area_ids="a20 a21 a22", row_id="P1D9ZT7S",
             soldout_class=False):
    cls = 'class="status_tr Soldout"' if soldout_class else 'class="status_tr"'
    return """<tr %s rel="%s" id="%s" style="cursor: pointer;">
	<td>
		<div class="colorblock" style="background-color:#DD94CD"></div>
	</td>
	<td data-title="票區：">%s</td>
	<td data-title="票價：">%s</td>
	<td data-title="空位：">%s</td>
</tr>""" % (cls, area_ids, row_id, name, price, remaining_text)


ROW_4 = area_row("平面特1區4680元", "4,680", "4")            # 空位 4
ROW_1 = area_row("2樓紫1C區4280元", "4,280", "1", "a27", "P1DA05KM")  # 空位 1
ROW_HOT = area_row("2樓黃2B區4280元", "4,280", "熱賣中", "a53", "P1DA05HE")  # 熱賣中
ROW_SOLD = area_row("2樓黃2C區4280元", "4,280", "已售完", "a54", "P1DA05FY")  # 已售完(無 Soldout class 的 safety net)


def make_config(ticket_number, area_keyword="", mode=bot.CONST_RANDOM):
    return {
        "advanced": {"verbose": False},
        "area_auto_select": {"mode": mode, "area_keyword": area_keyword},
        "ticket_number": ticket_number,
        "keyword_exclude": "",
    }


class TestKhamAreaAutoSelect(unittest.TestCase):

    def test_row_with_enough_remaining_clicked(self):
        """買 2 張時，空位 4 的區應保留並被點擊。"""
        row = FakeRow(ROW_4)
        is_need_refresh, is_price_assign = bot.kham_area_auto_select(
            FakeDriver([row]), "kham.com.tw", make_config(2), "")
        self.assertFalse(is_need_refresh)
        self.assertTrue(is_price_assign)
        self.assertTrue(row.clicked)

    def test_row_with_insufficient_remaining_skipped(self):
        """買 2 張時，空位 1 的區應排除 → 需 refresh。"""
        row = FakeRow(ROW_1)
        is_need_refresh, is_price_assign = bot.kham_area_auto_select(
            FakeDriver([row]), "kham.com.tw", make_config(2), "")
        self.assertTrue(is_need_refresh)
        self.assertFalse(is_price_assign)
        self.assertFalse(row.clicked)

    def test_remaining_1_kept_when_buying_1(self):
        """買 1 張時，空位 1 的區應保留（張數剛好夠）。"""
        row = FakeRow(ROW_1)
        is_need_refresh, is_price_assign = bot.kham_area_auto_select(
            FakeDriver([row]), "kham.com.tw", make_config(1), "")
        self.assertFalse(is_need_refresh)
        self.assertTrue(is_price_assign)
        self.assertTrue(row.clicked)

    def test_hot_selling_row_kept(self):
        """空位=熱賣中 的區應保留（非數字，不會被張數過濾排除）。"""
        row = FakeRow(ROW_HOT)
        is_need_refresh, is_price_assign = bot.kham_area_auto_select(
            FakeDriver([row]), "kham.com.tw", make_config(2), "")
        self.assertFalse(is_need_refresh)
        self.assertTrue(is_price_assign)
        self.assertTrue(row.clicked)

    def test_soldout_text_row_excluded(self):
        """含「售完」文字的區應排除（即使沒有 Soldout class）。"""
        row = FakeRow(ROW_SOLD)
        is_need_refresh, is_price_assign = bot.kham_area_auto_select(
            FakeDriver([row]), "kham.com.tw", make_config(2), "")
        self.assertTrue(is_need_refresh)
        self.assertFalse(is_price_assign)
        self.assertFalse(row.clicked)

    def test_area_keyword_filters_which_row_clicked(self):
        """area_keyword_item=平面特1區 時，只應點擊平面特1區。"""
        row1 = FakeRow(ROW_4)  # 平面特1區
        row2 = FakeRow(area_row("平面特2區4680元", "4,680", "88", "a29 a30 a31", "P1DA05KQ"))
        is_need_refresh, is_price_assign = bot.kham_area_auto_select(
            FakeDriver([row1, row2]), "kham.com.tw", make_config(2), "平面特1區")
        self.assertFalse(is_need_refresh)
        self.assertTrue(is_price_assign)
        self.assertTrue(row1.clicked)
        self.assertFalse(row2.clicked)


if __name__ == "__main__":
    unittest.main()
