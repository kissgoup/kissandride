#!/usr/bin/env python3
"""Unit tests for ibon SPA flow (2026 rewrite).

Real DOM/API facts the new code must handle (probed 2026-09-24, activity 39707):

- Step-2 page (UTK0201_000.aspx) renders the area table inside a CLOSED
  shadow DOM, but embeds the raw area JSON in a page <script> as:

      jsonData = '[{"PERFORMANCE_PRICE_AREA_ID":"...","GROUP_ID":"a8 a9",
                    "NAME":"1樓A區","PRICE":2080,"PRICE_STR":"2,080",
                    "SORT":1,"AMOUNT":"已售完",
                    "BACKGROUND_COLOR":"disabled","SEAT_STR":""}, ...]'

  (real sample below taken from the crawled page; click equivalent is
   UTK0201_001.aspx?PERFORMANCE_ID=..&GROUP_ID=..&PERFORMANCE_PRICE_AREA_ID=..)

- The SPA detail page (/ActivityInfo/Details/:id) loads sessions via
  POST /api/ActivityInfo/GetGameInfoList -> Item.GIHtmls[] with
  ShowSaleDate / VenueRegion / SoldOut / CanBuy / Href.
  (real sample below from ibon_api_log of activity 39707)

Verified behaviour:
  - parse_ibon_area_json extracts 8 areas from the real page source,
    [] when the block is absent (queue/landing page).
  - sold-out (AMOUNT='已售完' or BACKGROUND_COLOR='disabled') areas are
    never selected; 熱賣中 counts as buyable; numeric AMOUNT below
    ticket_number is skipped.
  - keyword matching runs on NAME + PRICE_STR with space-separated
    AND semantics, same as the legacy row matcher.
  - build_ibon_step3_url percent-encodes GROUP_ID ('a8 a9' -> a8%20a9).
  - parse_ibon_gamelist returns GIHtmls rows; bad JSON -> [].
  - buyable game = not SoldOut and CanBuy; row text for keyword matching
    joins ShowSaleDate + VenueRegion + GameInfoName on one line.
"""
import json
import os
import unittest
from urllib.parse import quote

import chrome_tixcraft as bot

# ---- real fixtures ---------------------------------------------------------

# Real area JSON (trimmed to the 8 real rows, values verbatim from crawl).
REAL_AREA_JSON = json.dumps([
    {"PERFORMANCE_PRICE_AREA_ID": "B0BX279C", "GROUP_ID": "a5 a6 a7",
     "NAME": "1樓A區", "PRICE": 2080, "PRICE_STR": "2,080",
     "COLOR": "-11765244", "SORT": 1, "AMOUNT": "已售完",
     "BACKGROUND_COLOR": "disabled", "SEAT_STR": ""},
    {"PERFORMANCE_PRICE_AREA_ID": "B0BX279F", "GROUP_ID": "a1 a2 a3",
     "NAME": "2樓A區", "PRICE": 2080, "PRICE_STR": "2,080",
     "COLOR": "-11765244", "SORT": 2, "AMOUNT": "已售完",
     "BACKGROUND_COLOR": "disabled", "SEAT_STR": ""},
    {"PERFORMANCE_PRICE_AREA_ID": "B0BX279K", "GROUP_ID": "a12",
     "NAME": "1樓A區視線遮蔽區", "PRICE": 1780, "PRICE_STR": "1,780",
     "COLOR": "-2255396", "SORT": 3, "AMOUNT": "14",
     "BACKGROUND_COLOR": "", "SEAT_STR": "class=action"},
    {"PERFORMANCE_PRICE_AREA_ID": "B0BX279L", "GROUP_ID": "a8 a9",
     "NAME": "1樓B區", "PRICE": 1780, "PRICE_STR": "1,780",
     "COLOR": "-14050874", "SORT": 4, "AMOUNT": "已售完",
     "BACKGROUND_COLOR": "disabled", "SEAT_STR": ""},
    {"PERFORMANCE_PRICE_AREA_ID": "B0BX279P", "GROUP_ID": "a15 a16 a17",
     "NAME": "2樓B區", "PRICE": 1780, "PRICE_STR": "1,780",
     "COLOR": "-14050874", "SORT": 5, "AMOUNT": "已售完",
     "BACKGROUND_COLOR": "disabled", "SEAT_STR": ""},
    {"PERFORMANCE_PRICE_AREA_ID": "B0CD1N2M", "GROUP_ID": "a10",
     "NAME": "1樓B區視線遮蔽區", "PRICE": 1480, "PRICE_STR": "1,480",
     "COLOR": "-2255396", "SORT": 6, "AMOUNT": "11",
     "BACKGROUND_COLOR": "", "SEAT_STR": "class=action"},
    {"PERFORMANCE_PRICE_AREA_ID": "B0BX279R", "GROUP_ID": "a18",
     "NAME": "2樓站席", "PRICE": 1480, "PRICE_STR": "1,480",
     "COLOR": "-2363078", "SORT": 7, "AMOUNT": "熱賣中",
     "BACKGROUND_COLOR": "", "SEAT_STR": "class=action"},
    {"PERFORMANCE_PRICE_AREA_ID": "B0BX279T", "GROUP_ID": "a4",
     "NAME": "愛心席", "PRICE": 1040, "PRICE_STR": "1,040",
     "COLOR": "-15003803", "SORT": 8, "AMOUNT": "已售完",
     "BACKGROUND_COLOR": "disabled", "SEAT_STR": ""},
], ensure_ascii=False)

STEP2_PAGE_HTML = (
    '<html><head><title>ibon售票系統</title></head><body>'
    '<input type="hidden" id="ctl00_ContentPlaceHolder1_PERFORMANCE_ID" '
    'value="B0BX25E9">'
    '<script>var jsonData = \'' + REAL_AREA_JSON + '\';'
    'UTK0201_000_init1(table, jsonData, ...);</script>'
    '</body></html>'
)

# Real GIHtmls rows from GetGameInfoList of activity 39707.
REAL_GAMELIST_BODY = json.dumps({
    "StatusCode": 0, "Message": "",
    "Item": {
        "Enable": False,
        "SystemBrowseType": 0,
        "GIHtmls": [
            {"ShowSaleDate": "2026/10/02(五) 19:30\r\n",
             "GameInfoName": "江美琪《傷心唱出來就沒事了》演唱會 2‧0 台北站",
             "VenueRegion": "Zepp New Taipei",
             "StartDT": "2026-09-22T20:00:00", "EndDT": "2026-10-02T19:30:00",
             "NowDT": "2026-09-24T17:34:30",
             "Href": "/ActivityInfo/GoTicketURL?GoUrl=https%3A%2F%2Forders.ibon.com.tw"
                     "%2Fapplication%2FUTK02%2FUTK0201_000.aspx%3FPERFORMANCE_ID"
                     "%3DB0BX25E9%26PRODUCT_ID%3DB0BS5Y0N",
             "SoldOut": False, "CanBuy": True, "Rush": 0, "PreQueue": 0,
             "GameLoginRequired": 0},
            {"ShowSaleDate": "2026/10/03(六) 18:30\r\n",
             "GameInfoName": "江美琪《傷心唱出來就沒事了》演唱會 2‧0 台北站",
             "VenueRegion": "Zepp New Taipei",
             "StartDT": "2026-09-22T20:00:00", "EndDT": "2026-10-03T18:30:00",
             "NowDT": "2026-09-24T17:34:30",
             "Href": "/ActivityInfo/GoTicketURL?GoUrl=https%3A%2F%2Forders.ibon.com.tw"
                     "%2Fapplication%2FUTK02%2FUTK0201_000.aspx%3FPERFORMANCE_ID"
                     "%3DB0BUJ497%26PRODUCT_ID%3DB0BS5Y0N",
             "SoldOut": False, "CanBuy": True, "Rush": 0, "PreQueue": 0,
             "GameLoginRequired": 0},
        ],
    },
}, ensure_ascii=False)

STEP2_URL = ("https://orders.ibon.com.tw/application/UTK02/UTK0201_000.aspx"
             "?PERFORMANCE_ID=B0BX25E9&PRODUCT_ID=B0BS5Y0N")


def config_dict_for_test(mode, ticket_number=2):
    return {
        "ticket_number": ticket_number,
        "area_auto_select": {"mode": mode, "area_keyword": "",
                             "area_keyword_exclude": ""},
        "date_auto_select": {"mode": mode, "date_keyword": ""},
        "advanced": {"verbose": False},
    }


# ---- parse_ibon_area_json --------------------------------------------------

class TestParseIbonAreaJson(unittest.TestCase):

    def test_parses_real_page_script_json(self):
        areas = bot.parse_ibon_area_json(STEP2_PAGE_HTML)
        self.assertEqual(len(areas), 8)
        self.assertEqual(areas[0]["NAME"], "1樓A區")
        self.assertEqual(areas[6]["PERFORMANCE_PRICE_AREA_ID"], "B0BX279R")

    def test_real_crawled_page_file_if_present(self):
        path = os.path.join(os.path.dirname(__file__), "ibon_utk02_page.html")
        if not os.path.exists(path):
            self.skipTest("ibon_utk02_page.html not present")
        with open(path, encoding="utf-8") as f:
            areas = bot.parse_ibon_area_json(f.read())
        self.assertEqual(len(areas), 8)
        names = [a["NAME"] for a in areas]
        self.assertIn("2樓站席", names)

    def test_returns_empty_when_no_json_block(self):
        self.assertEqual(bot.parse_ibon_area_json("<html><body></body></html>"), [])

    def test_returns_empty_on_broken_json(self):
        html = "<script>var jsonData = '[{broken';</script>"
        self.assertEqual(bot.parse_ibon_area_json(html), [])


# ---- ibon_area_usable ------------------------------------------------------

class TestIbonAreaUsable(unittest.TestCase):

    def test_sold_out_excluded(self):
        self.assertFalse(bot.ibon_area_usable(
            {"AMOUNT": "已售完", "BACKGROUND_COLOR": "disabled"}, 2))

    def test_hot_row_kept(self):
        self.assertTrue(bot.ibon_area_usable(
            {"AMOUNT": "熱賣中", "BACKGROUND_COLOR": ""}, 2))

    def test_numeric_amount_enough(self):
        self.assertTrue(bot.ibon_area_usable(
            {"AMOUNT": "14", "BACKGROUND_COLOR": ""}, 2))

    def test_numeric_amount_below_ticket_number_skipped(self):
        self.assertFalse(bot.ibon_area_usable(
            {"AMOUNT": "1", "BACKGROUND_COLOR": ""}, 2))


# ---- ibon_area_row_text / keyword match ------------------------------------

class TestIbonAreaKeywordMatch(unittest.TestCase):

    def test_row_text_joins_name_and_price(self):
        area = {"NAME": "2樓站席", "PRICE_STR": "1,480"}
        row_text = bot.ibon_area_row_text(area)
        self.assertIn("2樓站席", row_text)
        self.assertIn("1,480", row_text)

    def test_single_keyword_matches(self):
        area = {"NAME": "2樓站席", "PRICE_STR": "1,480"}
        self.assertTrue(bot.ibon_area_row_match(area, "站席"))

    def test_space_separated_keywords_are_and(self):
        area = {"NAME": "2樓站席", "PRICE_STR": "1,480"}
        self.assertTrue(bot.ibon_area_row_match(area, "站席 1,480"))
        self.assertFalse(bot.ibon_area_row_match(area, "站席 2,080"))

    def test_no_match(self):
        area = {"NAME": "1樓A區視線遮蔽區", "PRICE_STR": "1,780"}
        self.assertFalse(bot.ibon_area_row_match(area, "站席"))


# ---- build_ibon_step3_url --------------------------------------------------

class TestBuildIbonStep3Url(unittest.TestCase):

    def test_builds_url_with_encoded_group_id(self):
        url = bot.build_ibon_step3_url(
            STEP2_URL, "B0BX25E9", "a8 a9", "B0BX279L")
        self.assertTrue(url.startswith(
            "https://orders.ibon.com.tw/application/UTK02/UTK0201_001.aspx?"))
        self.assertIn("PERFORMANCE_ID=B0BX25E9", url)
        self.assertIn("GROUP_ID=a8%20a9", url)
        self.assertIn("PERFORMANCE_PRICE_AREA_ID=B0BX279L", url)

    def test_group_id_quoting_roundtrip(self):
        url = bot.build_ibon_step3_url(
            STEP2_URL, "P1", "a15 a16 a17", "A2")
        # the encoded value must decode back to the original group id
        from urllib.parse import urlparse, parse_qs
        q = parse_qs(urlparse(url).query)
        self.assertEqual(q["GROUP_ID"][0], "a15 a16 a17")
        self.assertEqual(quote("a15 a16 a17"), "a15%20a16%20a17")


# ---- parse_ibon_gamelist ---------------------------------------------------

class TestParseIbonGamelist(unittest.TestCase):

    def test_parses_real_response(self):
        rows = bot.parse_ibon_gamelist(REAL_GAMELIST_BODY)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["ShowSaleDate"].strip(), "2026/10/02(五) 19:30")

    def test_bad_json_returns_empty(self):
        self.assertEqual(bot.parse_ibon_gamelist("not json"), [])
        self.assertEqual(bot.parse_ibon_gamelist('{"Item": null}'), [])


# ---- ibon_game_buyable / ibon_game_row_text --------------------------------

class TestIbonGameFilter(unittest.TestCase):

    def test_buyable_rows(self):
        rows = bot.parse_ibon_gamelist(REAL_GAMELIST_BODY)
        for row in rows:
            self.assertTrue(bot.ibon_game_buyable(row))

    def test_soldout_or_not_buyable_excluded(self):
        self.assertFalse(bot.ibon_game_buyable({"SoldOut": True, "CanBuy": True}))
        self.assertFalse(bot.ibon_game_buyable({"SoldOut": False, "CanBuy": False}))

    def test_row_text_strips_crlf_and_joins(self):
        rows = bot.parse_ibon_gamelist(REAL_GAMELIST_BODY)
        text = bot.ibon_game_row_text(rows[0])
        self.assertNotIn("\r", text)
        self.assertNotIn("\n", text)
        self.assertIn("2026/10/02(五) 19:30", text)
        self.assertIn("Zepp New Taipei", text)

    def test_keyword_matches_one_session(self):
        rows = bot.parse_ibon_gamelist(REAL_GAMELIST_BODY)
        texts = [bot.ibon_game_row_text(r) for r in rows]
        matched = [t for t in texts
                   if bot.ibon_row_match_keyword(t, "10/03")]
        self.assertEqual(len(matched), 1)
        self.assertIn("10/03", matched[0])

    def test_keyword_multi_or_groups(self):
        rows = bot.parse_ibon_gamelist(REAL_GAMELIST_BODY)
        texts = [bot.ibon_game_row_text(r) for r in rows]
        matched = [t for t in texts
                   if bot.ibon_row_match_keyword(t, '"10/02","10/03"')]
        self.assertEqual(len(matched), 2)

    def test_keyword_empty_matches_all(self):
        rows = bot.parse_ibon_gamelist(REAL_GAMELIST_BODY)
        texts = [bot.ibon_game_row_text(r) for r in rows]
        matched = [t for t in texts if bot.ibon_row_match_keyword(t, "")]
        self.assertEqual(len(matched), 2)


# ---- resolve_ibon_game_href -------------------------------------------------

class TestResolveIbonGameHref(unittest.TestCase):

    def test_extracts_decoded_gourl_from_goticketurl_href(self):
        href = ("/ActivityInfo/GoTicketURL?GoUrl=https%3A%2F%2Forders.ibon.com.tw"
                "%2Fapplication%2FUTK02%2FUTK0201_000.aspx%3FPERFORMANCE_ID"
                "%3DB0BX25E9%26PRODUCT_ID%3DB0BS5Y0N")
        resolved = bot.resolve_ibon_game_href(href)
        self.assertEqual(
            resolved,
            "https://orders.ibon.com.tw/application/UTK02/UTK0201_000.aspx"
            "?PERFORMANCE_ID=B0BX25E9&PRODUCT_ID=B0BS5Y0N")

    def test_relative_href_gets_host_prefix(self):
        self.assertEqual(
            bot.resolve_ibon_game_href("/ActivityInfo/Details/39707"),
            "https://ticket.ibon.com.tw/ActivityInfo/Details/39707")

    def test_absolute_url_passthrough(self):
        self.assertEqual(
            bot.resolve_ibon_game_href("https://orders.ibon.com.tw/x"),
            "https://orders.ibon.com.tw/x")

    def test_empty_href(self):
        self.assertEqual(bot.resolve_ibon_game_href(""), "")


# ---- target selection mode -------------------------------------------------

class TestPickTargetArea(unittest.TestCase):

    AREAS = [
        {"NAME": "A區", "PRICE_STR": "1,000", "SORT": 1},
        {"NAME": "B區", "PRICE_STR": "2,000", "SORT": 2},
        {"NAME": "C區", "PRICE_STR": "3,000", "SORT": 3},
    ]

    def test_from_top(self):
        picked = bot.pick_ibon_area_target(self.AREAS, bot.CONST_FROM_TOP_TO_BOTTOM)
        self.assertEqual(picked["NAME"], "A區")

    def test_from_bottom(self):
        picked = bot.pick_ibon_area_target(self.AREAS, bot.CONST_FROM_BOTTOM_TO_TOP)
        self.assertEqual(picked["NAME"], "C區")

    def test_center(self):
        picked = bot.pick_ibon_area_target(self.AREAS, bot.CONST_CENTER)
        self.assertEqual(picked["NAME"], "B區")

    def test_random_returns_member(self):
        picked = bot.pick_ibon_area_target(self.AREAS, bot.CONST_RANDOM)
        self.assertIn(picked, self.AREAS)

    def test_empty_list(self):
        self.assertIsNone(bot.pick_ibon_area_target([], bot.CONST_FROM_TOP_TO_BOTTOM))


if __name__ == "__main__":
    unittest.main()
