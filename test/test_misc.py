#  This file is part of Recent changes Goat compatible Discord webhook (RcGcDw).
#
#  RcGcDw is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  RcGcDw is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with RcGcDw.  If not, see <http://www.gnu.org/licenses/>.

#  This file is part of Recent changes Goat compatible Discord webhook (RcGcDw).
#
#  RcGcDw is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  RcGcDw is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with RcGcDw.  If not, see <http://www.gnu.org/licenses/>.
import json
import sys
from unittest import TestCase
from src.exceptions import MediaWikiError
from src.misc import datafile, data_template, weighted_average, prepare_paths, parse_mw_request_info
from os.path import exists


class TestDataFile(TestCase):
    def test_generate_datafile(self):
        datafile.generate_datafile()
        self.assertTrue(exists(datafile.data_filename))
        with open(datafile.data_filename, "r") as df:
            contents = df.read()
        print(json.loads(contents))
        self.assertEqual(json.loads(contents), data_template)

    def test_load_datafile(self):
        self.assertEqual(datafile.load_datafile(), data_template)

    # def test_save_datafile(self):
    #     datafile["discussion_id"] = 321388838283
    #     datafile.save_datafile()
    #     with open(datafile.data_filename, "r") as df:
    #         contents = json.loads(df.read())
    #     self.assertEqual(contents["discussion_id"], 321388838283)


class Test(TestCase):
    def test_weighted_average(self):
        self.assertEqual(weighted_average(3, 5, 30), 7.5)

    def test_prepare_paths(self):
        self.assertEqual(prepare_paths("https://minecraft.fandom.com/blabhlldlasldllad", dry=True), "https://minecraft.fandom.com")
        self.assertEqual(prepare_paths("https://minecraft.fandom.com/wiki/Minecraft_Wiki", dry=True), "https://minecraft.fandom.com")
        self.assertEqual(prepare_paths("https://minecraft.fandom.com/", dry=True), "https://minecraft.fandom.com")

    def test_parse_mw_request_info(self):
        warning_data = """{"batchcomplete":"","warnings":[{"code":"unrecognizedvalues","key":"apiwarn-unrecognizedvalues","params":["list",{"list":["recentchange"],"type":"comma"},1],"module":"query"},{"code":"unrecognizedparams","key":"apierror-unrecognizedparams","params":[{"list":{"3":"rcshow","4":"rcprop","5":"rclimit","6":"rctype"},"type":"comma"},4],"module":"main"}]}"""
        warning_data = json.loads(warning_data)
        error_data = """{"errors":[{"code":"missingparam","key":"apierror-missingparam-at-least-one-of","params":[{"list":["<var>totitle</var>","<var>toid</var>","<var>torev</var>","<var>totext</var>","<var>torelative</var>","<var>toslots</var>"],"type":"text"},6],"module":"compare"}],"*":"See https://minecraft.fandom.com/pl/api.php for API usage. Subscribe to the mediawiki-api-announce mailing list at &lt;https://lists.wikimedia.org/mailman/listinfo/mediawiki-api-announce&gt; for notice of API deprecations and breaking changes."}"""
        error_data = json.loads(error_data)
        self.assertRaises(MediaWikiError, parse_mw_request_info, error_data, "dummy")
        with self.assertLogs("rcgcdw.misc", level="WARNING"):
            parse_mw_request_info(warning_data, "dummy")
        # with self.assertNoLogs("rcgcdw.misc", level="WARNING"):  # python 3.10
        #     parse_mw_request_info(legit_data, "dummy")
