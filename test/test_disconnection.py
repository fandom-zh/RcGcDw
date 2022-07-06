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
from test.test_utilities import inject_settings
from src.wiki import Wiki


class login_Testing(unittest.TestCase):
    wiki = Wiki(None, None)

    def test_connection_checker(self):
        self.assertTrue(self.wiki.check_connection(looped=True))

    def test_connection_tracker1(self):  # expands this test
        inject_settings("show_updown_messages", True)
        self.wiki.downtimecredibility = 0
        self.wiki.downtime_controller(True)
        self.assertTrue(self.wiki.downtimecredibility > 0)
