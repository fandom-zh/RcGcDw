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

import unittest
from src.configloader import settings
from test.test_utilities import inject_settings
from src.wiki import Wiki


def cleanup_func(func):
    def wrap(*args, **kwargs):
        login = settings["wiki_bot_login"]
        password = settings["wiki_bot_password"]
        func(*args, **kwargs)
        inject_settings("wiki_bot_login", login)
        inject_settings("wiki_bot_password", password)
        return func
    return wrap


class login_Testing(unittest.TestCase):
    wiki = Wiki(None, None)

    def test_success(self):
        self.wiki.logged_in = False
        self.wiki.log_in()
        self.assertTrue(self.wiki.logged_in)

    @cleanup_func
    def test_failure1(self):
        self.wiki.logged_in = False
        inject_settings("wiki_bot_login", "asdkaodhasofaufbasf")
        with self.assertLogs("rcgcdw.rc", level="ERROR"):
            self.wiki.log_in()

    @cleanup_func
    def test_failure2(self):
        self.wiki.logged_in = False
        inject_settings("wiki_bot_password", "lkkkkk")
        with self.assertLogs("rcgcdw.rc", level="ERROR"):
            self.wiki.log_in()
