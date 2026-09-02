#!/usr/bin/env python3
"""Unit tests for get_tixcraft_target_area remaining-count filtering.

Uses fake <a>/<font> objects (no browser) following unit_test_reload.py style.
The real DOM structure is verified by crawl4ai (tixcraft_page.html):
  <li class="select_form_a"><a id="23045_46">2樓C區 <font color="#FF0000">剩餘 35</font></a></li>
  <li class="select_form_a"><a id="23045_1">搖滾站區 <font color="#FF0000">熱賣中</font></a></li>
"""
import unittest

import chrome_tixcraft as bot


class FakeFont:
    def __init__(self, text):
        self.text = text


class FakeAreaLink:
    """Fake <a> element; innerHTML like the real tixcraft area row."""

    def __init__(self, inner_html, font_text=None):
        self.html = inner_html
        self.font = FakeFont(font_text) if font_text is not None else None

    def get_attribute(self, name):
        if name == 'innerHTML':
            return self.html
        return None

    def find_element(self, by, selector):
        if self.font is not None and selector == 'font':
            return self.font
        raise Exception("no such element: %s" % selector)


class FakeZone:
    def __init__(self, links):
        self.links = links

    def find_elements(self, by, tag):
        if tag == 'a':
            return self.links
        return []


def make_config(ticket_number):
    return {
        "advanced": {"verbose": False},
        "area_auto_select": {"mode": bot.CONST_RANDOM, "area_keyword": ""},
        "ticket_number": ticket_number,
        "keyword_exclude": "",
    }


AREA_HTML = '<a id="23045_46"><span>&nbsp;</span>2樓C區 <font color="#FF0000">剩餘 %s</font></a>'


class TestGetTixcraftTargetArea(unittest.TestCase):

    def test_buy_4_skips_area_with_3_remaining(self):
        """買 4 張時，剩餘 3 張的區要排除，熱賣中與剩餘 5 的保留。"""
        zone = FakeZone([
            FakeAreaLink(AREA_HTML % 3, "剩餘 3"),
            FakeAreaLink('<a id="23045_1"><span>&nbsp;</span>搖滾站區 <font color="#FF0000">熱賣中</font></a>', "熱賣中"),
            FakeAreaLink(AREA_HTML % 5, "剩餘 5"),
        ])
        is_need_refresh, matched_blocks = bot.get_tixcraft_target_area(zone, make_config(4), "")
        self.assertFalse(is_need_refresh)
        self.assertEqual(len(matched_blocks), 2)
        htmls = [row.html for row in matched_blocks]
        self.assertFalse(any("剩餘 3" in h for h in htmls))
        self.assertTrue(any("熱賣中" in h for h in htmls))
        self.assertTrue(any("剩餘 5" in h for h in htmls))

    def test_buy_2_keeps_area_with_2_remaining(self):
        """買 2 張時，剩餘 2 張的區要保留（張數剛好夠）。"""
        zone = FakeZone([
            FakeAreaLink(AREA_HTML % 2, "剩餘 2"),
            FakeAreaLink(AREA_HTML % 1, "剩餘 1"),
        ])
        is_need_refresh, matched_blocks = bot.get_tixcraft_target_area(zone, make_config(2), "")
        self.assertFalse(is_need_refresh)
        self.assertEqual(len(matched_blocks), 1)
        htmls = [row.html for row in matched_blocks]
        self.assertTrue(any("剩餘 2" in h for h in htmls))
        self.assertFalse(any("剩餘 1" in h for h in htmls))

    def test_buy_1_keeps_area_with_1_remaining(self):
        """買 1 張時，剩餘 1 張的區保留（現有行為不變）。"""
        zone = FakeZone([
            FakeAreaLink(AREA_HTML % 1, "剩餘 1"),
        ])
        is_need_refresh, matched_blocks = bot.get_tixcraft_target_area(zone, make_config(1), "")
        self.assertFalse(is_need_refresh)
        self.assertEqual(len(matched_blocks), 1)

    def test_empty_area_list_requires_refresh(self):
        """沒有任何 <a> 時，回傳 is_need_refresh=True（現有行為不變）。"""
        zone = FakeZone([])
        is_need_refresh, matched_blocks = bot.get_tixcraft_target_area(zone, make_config(2), "")
        self.assertTrue(is_need_refresh)
        self.assertIsNone(matched_blocks)


if __name__ == "__main__":
    unittest.main()
