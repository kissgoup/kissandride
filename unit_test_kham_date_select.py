#!/usr/bin/env python3
"""Unit tests for hkam_date_auto_select (kham 場次選擇，第 1 步).

Uses fake driver/row objects (no browser), following unit_test_reload.py /
unit_test_tixcraft_area_select.py style. The fake row HTML is taken from the
real crawled page (kham_step1.html):

  <tr>
      <td>2026/10/03(六)19:30</td>
      <td>...臺北小巨蛋...</td>
      <td data-th="票價(NT$)："><s><font color="lightblue">800</font></s>、3480、3880、4280、4680</td>
      <td><a href="javascript:;"><button class="red" onclick="top.location.href='UTK0204_.aspx?...';">立即訂購</button></a></td>
  </tr>

Verified behaviour:
  - header row (<th>, no <button>) excluded
  - 身障輪椅場 row (ALL prices wrapped in <s><font color="lightblue">) excluded
  - buyable row (has 立即訂購 button, at least one non-lightblue price) kept & clicked
  - date_keyword filters which performance is chosen
"""
import json
import unittest

import chrome_tixcraft as bot


class FakeButton:
    def __init__(self):
        self.clicked = False

    def is_enabled(self):
        return True

    def click(self):
        self.clicked = True


class FakeRow:
    """Fake <tr>; innerHTML like a real kham step-1 row."""

    def __init__(self, inner_html):
        self.html = inner_html
        self.button = FakeButton() if "<button" in inner_html else None

    def get_attribute(self, name):
        if name == "innerHTML":
            return self.html
        return None

    def find_element(self, by, selector):
        if selector == "button":
            if self.button is None:
                raise Exception("no such element: button")
            return self.button
        raise Exception("no such element: %s" % selector)


class FakeDriver:
    def __init__(self, rows):
        self.rows = rows

    def find_elements(self, by, selector):
        return self.rows


# ---- real row HTML from kham_step1.html ----------------------------------

HEADER_ROW = """<tr>
		<th scope="col">活動日期 Date and Time</th>
		<th scope="col">地點 Location</th>
		<th scope="col">票價 Price</th>
		<th scope="col">訂購 To order</th>
	</tr>"""

TAIPEI_ROW = """<tr>
		<td>
			2026/10/03(六)19:30

		</td>
		<td>

			<a id="PLACE_ADDRESS" href="http://maps.google.com.tw/maps?f=q&amp;hl=zh-TW&amp;q=%e5%8f%b0%e5%8c%97%e5%b0%8f%e5%b7%a8%e8%9b%8b%e7%ab%99" target="GoogleMap"><img src="https://imgs2.utiki.com.tw/Data/KHAM_RWD/images/locate.png" width="20" height="20" alt=""></a>&nbsp;
			<span id="PLACE_NAME">臺北小巨蛋</span>

		</td>
		<td data-th="票價(NT$)：">
			<s><font color="lightblue">800</font></s>、<s><font color="lightblue">1880</font></s>、<s><font color="lightblue">2480</font></s>、<s><font color="lightblue">2880</font></s>、3480、3880、4280、4680

		</td>
		<td>
			<a href="javascript:;"><button class="red" onclick="top.location.href='UTK0204_.aspx?PERFORMANCE_ID=P1D430L4&amp;PRODUCT_ID=P1D3G65D';return false;">立即訂購</button></a>
		</td>
	</tr>"""

HANDICAP_ROW = """<tr>
		<td>
			2026/10/03(六)19:30

		</td>
		<td>

			<span id="PLACE_NAME">臺北小巨蛋</span>
			<br>【身障輪椅場】國泰世華銀行 彭佳慧《數著時間的日子》巡迴演唱會
		</td>
		<td data-th="票價(NT$)：">
			<s><font color="lightblue">800</font></s>

		</td>
		<td>
			<a href="javascript:;"><button class="red" onclick="top.location.href='UTK0204_.aspx?PERFORMANCE_ID=P1DBFWUA&amp;PRODUCT_ID=P1D3G65D';return false;">立即訂購</button></a>
		</td>
	</tr>"""

KAOHSIUNG_ROW = """<tr>
		<td>
			2026/11/21(六)17:00

		</td>
		<td>

			<span id="PLACE_NAME">高雄巨蛋</span>

		</td>
		<td data-th="票價(NT$)：">
			<s><font color="lightblue">800</font></s>、<s><font color="lightblue">1880</font></s>、<s><font color="lightblue">2480</font></s>、2880、3480、3880、4280、4680

		</td>
		<td>
			<a href="javascript:;"><button class="red" onclick="top.location.href='UTK0204_.aspx?PERFORMANCE_ID=P1D4870B&amp;PRODUCT_ID=P1D3G65D';return false;">立即訂購</button></a>
		</td>
	</tr>"""


def make_config(mode=bot.CONST_RANDOM, date_keyword=""):
    # 真實 settings.json 的 date_keyword 存的是 JSON 轉義字串
    # （例如 "\"2026/11/21\""），因為程式內會 json.loads("[" + kw + "]")。
    # 這裡用 json.dumps 還原同樣的格式。
    if date_keyword:
        date_keyword = json.dumps(date_keyword)
    return {
        "advanced": {"verbose": False, "auto_reload_page_interval": 0},
        "date_auto_select": {"mode": mode, "date_keyword": date_keyword},
        "area_auto_select": {"mode": bot.CONST_RANDOM, "area_keyword": ""},
        "ticket_number": 2,
        "keyword_exclude": "",
        "tixcraft": {"auto_reload_coming_soon_page": False},
    }


class TestHkamDateAutoSelect(unittest.TestCase):

    def test_buyable_row_is_clicked(self):
        """台北場（3480+ 可買）應被選取並點下「立即訂購」。"""
        rows = [FakeRow(HEADER_ROW), FakeRow(TAIPEI_ROW)]
        is_date_assign = bot.hkam_date_auto_select(FakeDriver(rows), "kham.com.tw", make_config())
        self.assertTrue(is_date_assign)
        self.assertTrue(rows[1].button.clicked, "台北場的立即訂購應被點擊")

    def test_only_all_soldout_row_not_clicked(self):
        """只有整列票價已完售（身障輪椅場）時，不應點擊任何按鈕。"""
        rows = [FakeRow(HANDICAP_ROW)]
        is_date_assign = bot.hkam_date_auto_select(FakeDriver(rows), "kham.com.tw", make_config())
        self.assertFalse(is_date_assign)
        self.assertFalse(rows[0].button.clicked)

    def test_date_keyword_selects_kaohsiung(self):
        """date_keyword=2026/11/21 時，應選高雄巨蛋而非台北。"""
        taipei = FakeRow(TAIPEI_ROW)
        kaohsiung = FakeRow(KAOHSIUNG_ROW)
        rows = [taipei, kaohsiung]
        config = make_config(mode=bot.CONST_FROM_TOP_TO_BOTTOM, date_keyword="2026/11/21")
        is_date_assign = bot.hkam_date_auto_select(FakeDriver(rows), "kham.com.tw", config)
        self.assertTrue(is_date_assign)
        self.assertFalse(taipei.button.clicked, "台北場不應被點擊")
        self.assertTrue(kaohsiung.button.clicked, "高雄場應被點擊")

    def test_exclude_price_keyword_does_not_kill_buyable_row(self):
        """bug #1: keyword_exclude 含票價關鍵字（"4680"）時，可買列仍應被選取。

        第 1 步的列文字同時列出全部票價（800、…、4680），價格類排除字串
        用子字串比對會把整列誤殺 → 比對排除時應抽掉票價欄。
        """
        rows = [FakeRow(HEADER_ROW), FakeRow(TAIPEI_ROW)]
        config = make_config(mode=bot.CONST_FROM_TOP_TO_BOTTOM)
        config["keyword_exclude"] = '"輪椅","身障","4680"'  # 真實 settings 格式
        is_date_assign = bot.hkam_date_auto_select(FakeDriver(rows), "kham.com.tw", config)
        self.assertTrue(is_date_assign, "含 4680 票價的可買列不應被排除")
        self.assertTrue(rows[1].button.clicked)

    def test_exclude_seat_keyword_still_filters_handicap_row(self):
        """座位品質關鍵字（身障/輪椅）在第 1 步仍應濾掉身障列（場地欄比對）。"""
        rows = [FakeRow(HEADER_ROW), FakeRow(HANDICAP_ROW)]
        config = make_config(mode=bot.CONST_FROM_TOP_TO_BOTTOM)
        config["keyword_exclude"] = '"輪椅","身障","4680"'
        is_date_assign = bot.hkam_date_auto_select(FakeDriver(rows), "kham.com.tw", config)
        self.assertFalse(is_date_assign)
        self.assertFalse(rows[1].button.clicked, "身障列應被排除")


    def test_native_click_without_navigation_falls_back_to_js_click(self):
        """bug #3: uc.Chrome 原生 click 觸發 onclick 但導航沒發生時，
        應偵測 URL 沒變、回退 JS click 完成導航。"""
        class NavButton:
            def __init__(self):
                self.clicked = False
            def is_enabled(self):
                return True
            def click(self):
                # 模擬 uc bug：原生 click 只觸發 onclick、不導航
                self.clicked = True

        class NavRow(FakeRow):
            def __init__(self, inner_html):
                super().__init__(inner_html)
                self.button = NavButton()

        class NavDriver(FakeDriver):
            def __init__(self, rows):
                super().__init__(rows)
                self.url = "https://kham.com.tw/application/UTK02/UTK0201_00.aspx?PRODUCT_ID=P1D3G65D"
                self.js_clicked = False
            @property
            def current_url(self):
                return self.url
            def execute_script(self, js, *args):
                if "click()" in js:
                    self.js_clicked = True
                    self.url = "https://kham.com.tw/application/UTK02/UTK0204_.aspx?PERFORMANCE_ID=P1D430L4&PRODUCT_ID=P1D3G65D"
                return None
            def refresh(self):
                pass

        row = NavRow(TAIPEI_ROW)
        driver = NavDriver([row])
        config = make_config(mode=bot.CONST_FROM_TOP_TO_BOTTOM)
        config["tixcraft"] = {"auto_reload_coming_soon_page": False}
        is_date_assign = bot.hkam_date_auto_select(driver, "kham.com.tw", config)
        self.assertTrue(is_date_assign, "仍應回報已指派場次")
        self.assertTrue(driver.js_clicked, "應以 JS click 回退完成導航")
        self.assertTrue("UTK0204_" in driver.url, "導航應到 step-2（UTK0204_）")


if __name__ == "__main__":
    unittest.main()
