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

from unittest import TestCase, main
from src.api.util import sanitize_to_url, sanitize_to_markdown, clean_link


class Test(TestCase):
    def test_sanitize_to_url(self):
        self.assertEqual(sanitize_to_url("Breaking rcgcdw . \ / : ? = ) & - ~ this is a test)"),
                         "Breaking_rcgcdw_._%5C_/_:_%3F_%3D_%29_%26_-_~_this_is_a_test%29")

    def test_sanitize_to_markdown(self):
        self.assertEqual(sanitize_to_markdown(
            " This @MarkusRost [] is a **Markdown** te\"'''st __wow__ (I'm a link)[https://google.com/____]^^ ` nice {} comment\\\\foa*&&V^%A(!#)@!@I$Jfkasnfgamc,ajf ah wtf#####;h,a "),
                         " This \\@MarkusRost [] is a \\*\\*Markdown\\*\\* te\"\'\'\'st \\_\\_wow\\_\\_ (I\'m a link)[https\\:/\\/google.com/\\_\\_\\_\\_]^^ \\` nice \\{\\} comment\\\\\\\\foa\\*&&V^%A(!#)\\@!\\@I$Jfkasnfgamc,ajf ah wtf#####;h,a ")

    def test_clean_link(self):
        self.assertEqual(clean_link("https://example.com"), "<https://example.com>")


if __name__ == '__main__':
    main()
