#!/usr/bin/env python3
#encoding=utf-8
"""Unit tests for util.link_settings_file_to_extension.

設計目標（2026-09-03）: 擴充功能不再維護獨立 settings.json 副本，
改以 hardlink 指向根目錄唯一主本：
  - 主本不存在 -> 不動作、回 False
  - data/settings.json 缺 -> 建 hardlink
  - data/settings.json 是舊式獨立副本（dump 遺留）-> 換成 hardlink
  - 主本原地改寫（save_json 用 open('w')）時，經連結讀到最新內容
"""
import os
import tempfile
import unittest

import util


class TestLinkSettingsFileToExtension(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = self._tmp.name
        self.master = os.path.join(self.tmp, "settings.json")
        with open(self.master, "w", encoding="utf-8") as f:
            f.write('{"homepage": "https://tixcraft.com/"}')
        self.ext = os.path.join(self.tmp, "webdriver", "ext_1.0.0")
        self.link = os.path.join(self.ext, "data", "settings.json")

    def tearDown(self):
        self._tmp.cleanup()

    def test_creates_link_when_missing(self):
        """無 data 目錄、無檔案 -> 建目錄與 hardlink，內容等同主本。"""
        ret = util.link_settings_file_to_extension(self.master, self.ext)
        self.assertTrue(ret)
        self.assertTrue(os.path.isfile(self.link))
        self.assertTrue(os.path.samefile(self.master, self.link), "應與主本同檔（hardlink）")

    def test_replaces_stale_copy_with_link(self):
        """舊式獨立副本（dump 遺留、內容可為舊值）-> 換成指向主本的 hardlink。"""
        os.makedirs(os.path.dirname(self.link))
        with open(self.link, "w", encoding="utf-8") as f:
            f.write('{"homepage": "https://old.example/"}')
        ret = util.link_settings_file_to_extension(self.master, self.ext)
        self.assertTrue(ret)
        self.assertTrue(os.path.samefile(self.master, self.link), "舊副本應被換成 hardlink")
        with open(self.link, encoding="utf-8") as f:
            self.assertIn("tixcraft.com", f.read(), "內容應為主本內容")

    def test_master_edit_in_place_visible_through_link(self):
        """主本原地改寫後，經連結讀到最新內容（同一檔案）。"""
        util.link_settings_file_to_extension(self.master, self.ext)
        with open(self.master, "w", encoding="utf-8") as f:
            f.write('{"homepage": "https://kham.com.tw/"}')
        with open(self.link, encoding="utf-8") as f:
            self.assertIn("kham.com.tw", f.read())

    def test_missing_master_returns_false(self):
        """主本不存在 -> 回 False、不建任何檔案。"""
        ret = util.link_settings_file_to_extension(
            os.path.join(self.tmp, "nope.json"), self.ext)
        self.assertFalse(ret)
        self.assertFalse(os.path.exists(self.link))


if __name__ == "__main__":
    unittest.main()
