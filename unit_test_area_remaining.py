#!/usr/bin/env python3
"""Unit tests for parse_tixcraft_area_remaining — parsed seat-count from <font> text."""
import sys
import unittest

import chrome_tixcraft as bot


class TestParseTixcraftAreaRemaining(unittest.TestCase):
    """Test the helper that extracts seat-remaining number from a font element's text."""

    # ── RED Phase 1: parse_tixcraft_area_remaining doesn't exist yet ──

    def test_parse_remaining_chinese(self):
        """parse_tixcraft_area_remaining('剩餘 35') → 35"""
        result = bot.parse_tixcraft_area_remaining("剩餘 35")
        self.assertEqual(result, 35)

    def test_parse_remaining_with_spaces(self):
        """parse_tixcraft_area_remaining('剩餘   7') → 7 (extra whitespace)"""
        result = bot.parse_tixcraft_area_remaining("剩餘   7")
        self.assertEqual(result, 7)

    def test_parse_remaining_english(self):
        """parse_tixcraft_area_remaining('18 seat(s) remaining') → 18"""
        result = bot.parse_tixcraft_area_remaining("18 seat(s) remaining")
        self.assertEqual(result, 18)

    def test_parse_hot_sale_none(self):
        """parse_tixcraft_area_remaining('熱賣中') → None (hot sale, no count shown)"""
        result = bot.parse_tixcraft_area_remaining("熱賣中")
        self.assertIsNone(result)

    def test_parse_on_sale_none(self):
        """parse_tixcraft_area_remaining('開放中') → None"""
        result = bot.parse_tixcraft_area_remaining("開放中")
        self.assertIsNone(result)

    def test_parse_unknown_strips_text(self):
        """parse_tixcraft_area_remaining on unknown text returns None (never crash)."""
        result = bot.parse_tixcraft_area_remaining("some unknown marker")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
