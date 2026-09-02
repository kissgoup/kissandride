#!/usr/bin/env python3
#encoding=utf-8
"""Unit tests for ticketplus_date_auto_select 的場次列查詢韌性.

真實 DOM（tp3_activity.html, 2026-09-02 crawl）:
  div#buyTicket > div.sesstion-item > div.row   -> 場次列（內含 button.nextBtn 立即購買）
實測故障（2026-09-01 probe、2026-09-02 probe2 整個 session）:
  div.sesstion-item 存在（2 個）、button.nextBtn 可按，但
  'div#buyTicket > div.sesstion-item > div.row' 回傳 0 列 ->
  bot 印 "empty date item, need retry." 後放棄該輪。
修復方向: 查詢由窄到寬階梯式退回（去 #buyTicket 界定 -> 整個 sesstion-item），
任一層查到列即用該層；全空才交回原 None 判定。
"""
import unittest

import chrome_tixcraft as bot

SCOPED = 'div#buyTicket > div.sesstion-item > div.row'
UNSCOPED = 'div.sesstion-item > div.row'
ITEM = 'div.sesstion-item'

ROW_HTML = (
    '<div class="row pa-4 flex-column flex-sm-row no-gutters">'
    '<div class="col-sm-10 col-md-10 col-12"><div class="row mx-0 no-gutters">'
    '<div class="col-sm-12 col-md-4 col-12">測試場次（10/9場次）</div>'
    '<div class="col-sm-12 col-md-2 col-12"><div class="d-flex"><div>2026-10-09(五)</div></div></div>'
    '</div></div>'
    '<div class="font-weight-bold col-sm-2 col-md-2 col-12 align-self-center">'
    '<button type="button" class="nextBtn float-right v-btn v-btn--block v-btn--has-bg">'
    '<span class="v-btn__content">立即購買</span></button>'
    '</div></div>'
)


class FakeBuyButton:
    def __init__(self):
        self.click_count = 0

    def is_enabled(self):
        return True

    def click(self):
        self.click_count += 1


class FakeSessionRow:
    """div.row 或整個 div.sesstion-item；find_element('button') 找下一代按鈕。"""

    def __init__(self, html=ROW_HTML):
        self._html = html
        self.button = FakeBuyButton()

    def get_attribute(self, name):
        if name == "innerHTML":
            return self._html
        return None

    def find_element(self, by, selector):
        if selector == "button":
            return self.button
        raise Exception("no such element: %s" % selector)


def make_config():
    return {
        "advanced": {"verbose": False},
        "date_auto_select": {"mode": "from top to bottom", "date_keyword": ""},
        "tixcraft": {"pass_date_is_sold_out": True, "auto_reload_coming_soon_page": False},
        "keyword_exclude": "",
    }


class FlakeDriver:
    """模擬故障態: 窄 selector 回 0 列，寬 selector 才找得到。
    find_elements 依查詢字串決定回傳；未預期查詢一律回 []。"""

    def __init__(self, scoped=0, unscoped=0, item=0):
        self.counts = {SCOPED: scoped, UNSCOPED: unscoped, ITEM: item}
        self.rows = []

    def find_elements(self, by, selector):
        n = self.counts.get(selector, 0)
        if len(self.rows) < sum(self.counts.values()):
            self.rows = [FakeSessionRow() for _ in range(sum(self.counts.values()))]
        return self.rows[:n]


class TestTicketplusDateAutoSelect(unittest.TestCase):

    def test_normal_scoped_query_still_works(self):
        """迴歸保護: 現行 selector 查到列時行為不變（點到立即購買）。"""
        driver = FlakeDriver(scoped=2)
        ret = bot.ticketplus_date_auto_select(driver, make_config())
        self.assertTrue(ret)
        self.assertEqual(driver.rows[0].button.click_count, 1)

    def test_scoped_empty_falls_back_to_unscoped(self):
        """故障態 A: #buyTicket 界定查 0 列，但 div.sesstion-item > div.row 找得到
        -> 應退回寬 selector 完成點擊，而非放棄該輪。"""
        driver = FlakeDriver(scoped=0, unscoped=2)
        ret = bot.ticketplus_date_auto_select(driver, make_config())
        self.assertTrue(ret)
        self.assertEqual(driver.rows[0].button.click_count, 1)

    def test_inner_wrapped_falls_back_to_sesstion_item(self):
        """故障態 B: 連 div.row 都不在預期層級時，整個 div.sesstion-item 仍含
        button 後代 -> 應以 item 為列完成點擊。"""
        driver = FlakeDriver(scoped=0, unscoped=0, item=2)
        ret = bot.ticketplus_date_auto_select(driver, make_config())
        self.assertTrue(ret)
        self.assertEqual(driver.rows[0].button.click_count, 1)

    def test_all_empty_returns_false(self):
        """全部查無列 -> 維持原行為回 False，不點任何東西、不丟例外。"""
        driver = FlakeDriver(scoped=0, unscoped=0, item=0)
        ret = bot.ticketplus_date_auto_select(driver, make_config())
        self.assertFalse(ret)
        for row in driver.rows:
            self.assertEqual(row.button.click_count, 0)


if __name__ == "__main__":
    unittest.main()
