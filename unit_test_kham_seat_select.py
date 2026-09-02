#!/usr/bin/env python3
"""Unit tests for kham step-3 seat-map selection (UTK0205 座位表頁).

真實 DOM（crawl4ai 爬 UTK0205_.aspx?...PERFORMANCE_PRICE_AREA_ID= 驗證）:
  - 票別按鈕 <div class="ticket"><button onclick="setType(...)">原價-NT$4,280...
  - 座位表 <table id="TBL">，空位 <td class="empty right">、已選 <td class="empty selected ...">、
    已售 <td class="people right">；bindSeat 的 jQuery click 會把 #SELECT_COUNT +1
  - 已選計數 <span id="SELECT_COUNT">0</span>
  - 登入區 #LOGIN_ID / #LOGIN_PWD（未登入時 addShoppingCart 必填）

實測 bug：bot 點完「原價」後沒有去點座位 → addShoppingCart 彈「請選擇【座位】！」；
且舊程式以 #AMOUNT 判斷張數，但真實 kham 頁面從頭到尾沒有 #AMOUNT。
"""
import unittest

import chrome_tixcraft as bot


class FakeSeatCell:
    """模擬座位 <td>；execute_script JS click 後依真頁行為切換狀態。"""

    def __init__(self, classes):
        self.classes = classes

    def get_attribute(self, name):
        if name == "class":
            return self.classes
        return None

    def is_displayed(self):
        return True


class FakeCounterEl:
    def __init__(self, driver):
        self.driver = driver

    @property
    def text(self):
        return str(self.driver.selected_count)


class FakeSeatRow:
    """模擬座位表的一列 <tr>；row.find_elements('td') 回傳該列的座位。"""

    def __init__(self, cells):
        self.cells = cells

    def find_elements(self, by, selector):
        if selector == "td":
            return list(self.cells)
        return []


class FakeSeatDriver:
    """find_elements 回傳所有座位（含 people/selected），
    execute_script 的 JS click 模擬真頁 toggle：empty→selected(+1)、
    selected→empty(-1)。#SELECT_COUNT 即 selected_count。"""

    def __init__(self, seats, selected_count=0, with_counter=True, curr_type="P1DA05FN", rows=None):
        self.seats = seats
        self.selected_count = selected_count
        self.with_counter = with_counter
        self.curr_type = curr_type
        self.rows = rows
        self.click_count = 0

    def find_element(self, by, selector):
        if "#SELECT_COUNT" in selector:
            if not self.with_counter:
                raise Exception("no such element: %s" % selector)
            return FakeCounterEl(self)
        raise Exception("no such element: %s" % selector)

    def find_elements(self, by, selector):
        if selector == "table#TBL > tbody > tr":
            if self.rows is None:
                return []
            return list(self.rows)
        return list(self.seats)

    def execute_script(self, js, *args):
        # 讀取 currType 全域（kham_get_curr_type）
        if "currType" in js and "click" not in js:
            return self.curr_type
        if "click" in js and len(args) >= 1:
            seat = args[0]
            self.click_count += 1
            if seat.classes.startswith("empty") and "selected" not in seat.classes:
                rest = seat.classes.split(" ", 1)[1] if " " in seat.classes else ""
                seat.classes = ("empty selected " + rest).strip()
                self.selected_count += 1
            else:
                # 已選座位再點一次 = 取消選位（真頁 toggle 行為）
                rest = seat.classes.replace("empty selected", "").strip()
                seat.classes = ("empty " + rest).strip()
                self.selected_count -= 1
            return None
        return None


def make_config(ticket_number=2, allow_non_adjacent=False):
    return {
        "advanced": {
            "verbose": False,
            "disable_adjacent_seat": allow_non_adjacent,
        },
        "ticket_number": ticket_number,
    }


def make_login_config():
    return {
        "advanced": {
            "verbose": False,
            "kham_account": "tester@example.com",
            "kham_password_plaintext": "secret123",
            "kham_password": "",
        }
    }


class TestKhamSeatAutoSelect(unittest.TestCase):

    def test_clicks_empty_seats_until_target(self):
        """空位足夠時，應點到 SELECT_COUNT == ticket_number 為止。"""
        seats = [FakeSeatCell("empty right") for _ in range(4)]
        driver = FakeSeatDriver(seats)
        ret = bot.kham_seat_auto_select(driver, make_config(ticket_number=2))
        self.assertTrue(ret)
        self.assertEqual(driver.selected_count, 2)
        self.assertEqual(driver.click_count, 2, "不應多點")

    def test_skips_people_and_selected_seats(self):
        """people（已售）與 empty selected（已選）不應被點。"""
        seats = [
            FakeSeatCell("people right"),        # 已售
            FakeSeatCell("empty selected up"),   # 已選（bot 填的）
            FakeSeatCell("people left"),
            FakeSeatCell("empty left"),
        ]
        driver = FakeSeatDriver(seats, selected_count=1)
        ret = bot.kham_seat_auto_select(driver, make_config(ticket_number=2))
        self.assertTrue(ret)
        self.assertEqual(driver.selected_count, 2)
        # 只有 1 個空位被點：people 與已選座位都跳過
        self.assertFalse(seats[0].classes.startswith("people selected"))
        self.assertEqual(seats[1].classes.count("selected"), 1, "已選座位不應被取消")

    def test_already_enough_seats_clicks_nothing(self):
        """已選數量達標時不應再點任何座位。"""
        seats = [FakeSeatCell("empty right") for _ in range(3)]
        driver = FakeSeatDriver(seats, selected_count=3)
        ret = bot.kham_seat_auto_select(driver, make_config(ticket_number=2))
        self.assertTrue(ret)
        self.assertEqual(driver.click_count, 0)

    def test_returns_none_when_no_seat_map(self):
        """頁面沒有 #SELECT_COUNT（非座位表頁）應回傳 None，不丟例外。"""
        driver = FakeSeatDriver([], with_counter=False)
        ret = bot.kham_seat_auto_select(driver, make_config())
        self.assertIsNone(ret)

    def test_short_when_not_enough_empty_seats(self):
        """空位不足 ticket_number 時應回傳 False（不亂點已售座位）。"""
        seats = [FakeSeatCell("people right"), FakeSeatCell("empty left")]
        driver = FakeSeatDriver(seats)
        ret = bot.kham_seat_auto_select(driver, make_config(ticket_number=2))
        self.assertFalse(ret)
        self.assertEqual(driver.selected_count, 1)

    def test_no_click_when_curr_type_empty(self):
        """bug #4: 票別（setType/currType）未生效時不可點座位，
        否則真頁會彈「請先選擇【票別】！」對話框無限循環。"""
        seats = [FakeSeatCell("empty right") for _ in range(4)]
        driver = FakeSeatDriver(seats, curr_type="")
        ret = bot.kham_seat_auto_select(driver, make_config(ticket_number=2))
        self.assertFalse(ret)
        self.assertEqual(driver.click_count, 0, "currType 空時不應點任何座位")
        self.assertEqual(driver.selected_count, 0)

    # ---- 連續座位（disable_adjacent_seat = False 時）--------------------

    @staticmethod
    def make_grid_driver(row_class_lists, **kwargs):
        """由每列 class list 建立 FakeSeatDriver（rows + flat seats 同步）。"""
        rows = [FakeSeatRow([FakeSeatCell(c) for c in classes]) for classes in row_class_lists]
        flat = [cell for row in rows for cell in row.cells]
        return FakeSeatDriver(flat, rows=rows, **kwargs)

    def test_prefers_adjacent_run_in_same_row(self):
        """bug #5: 未啟用「允許不連續座位」時，應選同一列連續空位，
        而不是 document order 前兩個散位（實測選到 17排25號+18排27號）。"""
        driver = self.make_grid_driver([
            ["people right", "empty left", "people left", "empty right"],  # 散位，不選
            ["empty right", "empty right", "people right", "empty left"],  # 這列開頭兩個連續
        ])
        ret = bot.kham_seat_auto_select(driver, make_config(ticket_number=2))
        self.assertTrue(ret)
        self.assertEqual(driver.selected_count, 2)
        row1, row2 = driver.rows
        for cell in row1.cells:
            self.assertNotIn("selected", cell.classes, "散位的列不應被點")
        self.assertIn("selected", row2.cells[0].classes)
        self.assertIn("selected", row2.cells[1].classes, "應選同一列相鄰的兩個空位")

    def test_no_adjacent_run_returns_false(self):
        """沒有任何一列有足夠連續空位時，遵守設定不應硬選散位。"""
        driver = self.make_grid_driver([
            ["empty right", "people right", "empty left"],
            ["people left", "empty left", "people left"],
        ])
        ret = bot.kham_seat_auto_select(driver, make_config(ticket_number=2))
        self.assertFalse(ret)
        self.assertEqual(driver.click_count, 0, "不應點散位破壞連續座位要求")
        self.assertEqual(driver.selected_count, 0)

    def test_allow_non_adjacent_keeps_greedy(self):
        """啟用「允許不連續座位」（disable_adjacent_seat=True）時，沿用逐一選位。"""
        driver = self.make_grid_driver([
            ["empty right", "people right", "empty left"],
            ["people left", "empty left", "people left"],
        ])
        ret = bot.kham_seat_auto_select(driver, make_config(ticket_number=2, allow_non_adjacent=True))
        self.assertTrue(ret)
        self.assertEqual(driver.selected_count, 2)

    def test_single_seat_needs_no_adjacency(self):
        """只買 1 張時任何單一空位都算連續。"""
        driver = self.make_grid_driver([
            ["people right", "empty left"],
        ])
        ret = bot.kham_seat_auto_select(driver, make_config(ticket_number=1))
        self.assertTrue(ret)
        self.assertEqual(driver.selected_count, 1)

    def test_partial_selection_falls_back_to_greedy(self):
        """已有部分選位（人工先點的）時，用補點方式選完，不要卡死。"""
        driver = self.make_grid_driver([
            ["empty right", "people right", "empty left"],
        ], selected_count=1)
        # 手動把第一個標成已選（模擬 SELECT_COUNT=1 的來源）
        driver.rows[0].cells[0].classes = "empty selected right"
        ret = bot.kham_seat_auto_select(driver, make_config(ticket_number=2))
        self.assertTrue(ret)
        self.assertEqual(driver.selected_count, 2)


class FakePriceButton:
    """模擬 div.ticket 內的「原價」按鈕。working=True 時原生 click 會生效
    （onclick setType）；False 時靜默失效（uc.Chrome 實測 bug）。"""

    def __init__(self, driver, working=False):
        self.driver = driver
        self.working = working

    def is_displayed(self):
        return True

    def is_enabled(self):
        return True

    def click(self):
        self.driver.native_clicks += 1
        if self.working:
            self.driver.curr_type = "P1DA05FN"


class FakePriceTypeDriver:
    """模擬 UTK0205 頁面：供 kham_select_regular_price_area 測試。
    WebDriverWait(EC.element_to_be_clickable) 會走 find_elements。"""

    def __init__(self, working=False):
        self.button = FakePriceButton(self, working=working)
        self.curr_type = ""
        self.native_clicks = 0
        self.js_clicks = 0
        self.current_url = "https://kham.com.tw/application/UTK02/UTK0205_.aspx?PERFORMANCE_ID=X"

    def find_element(self, by, selector):
        return self.button

    def find_elements(self, by, selector):
        return [self.button]

    def execute_script(self, js, *args):
        if "currType" in js and "click" not in js:
            return self.curr_type
        if "click" in js and len(args) >= 1:
            # JS click 一定會觸發 inline onclick（setType）
            self.js_clicks += 1
            self.curr_type = "P1DA05FN"
        return None


class TestKhamSelectRegularPriceArea(unittest.TestCase):

    def test_native_click_silent_noop_falls_back_to_js(self):
        """bug #4: uc.Chrome 原生 click 靜默失效（不拋例外）時，
        應驗證 currType 未設定並回退 JS click 觸發 setType。"""
        driver = FakePriceTypeDriver(working=False)
        ret = bot.kham_select_regular_price_area(driver, {"advanced": {"verbose": False}})
        self.assertTrue(ret)
        self.assertEqual(driver.curr_type, "P1DA05FN", "setType 應經 JS 回退生效")
        self.assertEqual(driver.js_clicks, 1, "應以 JS click 回退")

    def test_working_native_click_does_not_js_click_again(self):
        """原生 click 生效（currType 已設定）時不應再 JS click。"""
        driver = FakePriceTypeDriver(working=True)
        ret = bot.kham_select_regular_price_area(driver, {"advanced": {"verbose": False}})
        self.assertTrue(ret)
        self.assertEqual(driver.curr_type, "P1DA05FN")
        self.assertEqual(driver.js_clicks, 0, "不應重複 JS click")


class FakeLoginField:
    """模擬 #LOGIN_ID / #LOGIN_PWD；send_keys 靜默 no-op（同 #CHK 的 uc.Chrome bug）。"""

    def __init__(self):
        self.value = ""

    def get_attribute(self, name):
        if name == "value":
            return self.value
        return None

    def clear(self):
        self.value = ""

    def send_keys(self, keys):
        pass  # 靜默失效

    def set_value(self, v):
        self.value = v


class FakeLoginDriver:
    def __init__(self, login_id=None, login_pwd=None):
        self.login_id = login_id
        self.login_pwd = login_pwd
        self.scripts_run = 0

    def find_element(self, by, selector):
        if selector == "#LOGIN_ID":
            if self.login_id is None:
                raise Exception("no such element")
            return self.login_id
        if selector == "#LOGIN_PWD":
            if self.login_pwd is None:
                raise Exception("no such element")
            return self.login_pwd
        raise Exception("no such element: %s" % selector)

    def execute_script(self, js, *args):
        self.scripts_run += 1
        if len(args) >= 2:
            args[0].set_value(args[1])
        return None


class TestKhamSeatLoginFill(unittest.TestCase):

    def test_fills_login_with_js_fallback(self):
        """send_keys 靜默失效時，應以 JS 回退填入帳號密碼。"""
        el_id, el_pwd = FakeLoginField(), FakeLoginField()
        driver = FakeLoginDriver(el_id, el_pwd)
        ret = bot.kham_keyin_seat_login(driver, make_login_config())
        self.assertTrue(ret)
        self.assertEqual(el_id.value, "tester@example.com")
        self.assertEqual(el_pwd.value, "secret123")
        self.assertGreaterEqual(driver.scripts_run, 2, "兩個欄位都應走 JS 回退")

    def test_does_not_overwrite_existing_value(self):
        """欄位已有值（使用者自行輸入）時不應覆寫。"""
        el_id, el_pwd = FakeLoginField(), FakeLoginField()
        el_id.value = "my own account"
        driver = FakeLoginDriver(el_id, el_pwd)
        ret = bot.kham_keyin_seat_login(driver, make_login_config())
        self.assertFalse(ret, "帳號被占用未填入應回報 False")
        self.assertEqual(el_id.value, "my own account")

    def test_missing_fields_return_false_without_crash(self):
        """頁面沒有登入區（已登入）時應回傳 False 且不丟例外。"""
        driver = FakeLoginDriver(None, None)
        ret = bot.kham_keyin_seat_login(driver, make_login_config())
        self.assertFalse(ret)


if __name__ == "__main__":
    unittest.main()
