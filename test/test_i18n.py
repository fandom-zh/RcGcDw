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

from test.test_utilities import inject_settings
import src.i18n
import unittest


class i18nTesting(unittest.TestCase):
    def test_language_output_polish(self):
        inject_settings("lang", "pl")
        src.i18n.load_languages()  # reload languages with new language
        self.assertEqual(src.i18n.rcgcdw.gettext("Daily overview"), "Podsumowanie dnia")

    def test_language_output_english(self):
        inject_settings("lang", "en")
        src.i18n.load_languages()  # reload languages with new language
        self.assertEqual(src.i18n.rcgcdw.gettext("Daily overview"), "Daily overview")
