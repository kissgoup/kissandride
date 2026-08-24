#!/usr/bin/env python3
#encoding=utf-8
# 單元級驗證: ticketplus_date_auto_select 的 reload 調優分支。
# 不啟動瀏覽器, 使用 fake driver/row/button。
import sys

import chrome_tixcraft as bot

ROW_HTML_BUY = '<div class="row pa-4"><span class="v-btn__content">立即購買</span></div>'
ROW_HTML_COMING = '<button disabled><span>尚未開賣</span></button>'
ROW_HTML_SOLDOUT = '<button><span>立即購買</span></button><span>銷售一空</span>'

CONFIG = {
    "advanced": {"verbose": False, "auto_reload_page_interval": 0.5},
    "date_auto_select": {"mode": "from top to bottom", "date_keyword": ""},
    "tixcraft": {"pass_date_is_sold_out": True, "auto_reload_coming_soon_page": True},
    "keyword_exclude": "",
}


class FakeButtonDisabled:
    def is_enabled(self):
        return False


class FakeButtonEnabled:
    def is_enabled(self):
        return True

    def click(self):
        pass


class FakeRow:
    def __init__(self, html, button):
        self.html = html
        self.button = button

    def get_attribute(self, name):
        if name == 'innerHTML':
            return self.html
        return None

    def find_element(self, by, selector):
        if selector == 'button':
            return self.button
        raise Exception("no such element: %s" % selector)


class FakeDriver:
    def __init__(self, rows):
        self.rows = rows
        self.refresh_count = 0

    def find_elements(self, by, css):
        if css == 'div#buyTicket > div.sesstion-item > div.row':
            return self.rows
        return []

    def get_log(self, kind):
        return []

    def refresh(self):
        self.refresh_count += 1


def run(name, rows, expect_ret, expect_refresh):
    bot.get_random_delay = lambda cfg: 0.0
    bot.time.sleep = lambda s: None
    d = FakeDriver(rows)
    ret = bot.ticketplus_date_auto_select(d, CONFIG)
    ok = (ret == expect_ret) and (d.refresh_count == expect_refresh)
    print("[%s] ret=%s refresh=%d expect(ret=%s, refresh=%d) -> %s"
          % (name, ret, d.refresh_count, expect_ret, expect_refresh, "PASS" if ok else "FAIL"))
    return ok


results = []
# 1) 目標按鈕 disabled(尚未開賣) -> 應觸發 reload, 不點擊
results.append(run("disabled-button(coming soon) -> reload",
                   [FakeRow(ROW_HTML_BUY, FakeButtonDisabled())],
                   expect_ret=False, expect_refresh=1))
# 2) 目標按鈕 enabled(可購買) -> 應點擊, 不 reload
results.append(run("enabled-button -> click, no reload",
                   [FakeRow(ROW_HTML_BUY, FakeButtonEnabled())],
                   expect_ret=True, expect_refresh=0))
# 3) 全部售完(銷售一空) -> 原有 reload 行為不變(回歸)
results.append(run("all sold out -> reload (regression)",
                   [FakeRow(ROW_HTML_SOLDOUT, FakeButtonDisabled())],
                   expect_ret=False, expect_refresh=1))

print("----")
print("ALL PASS" if all(results) else "SOME FAILED")
sys.exit(0 if all(results) else 1)
