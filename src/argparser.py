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

import argparse

parser = argparse.ArgumentParser(description="Start RcGcDw")
parser.add_argument("--test", action='store_true', help="mode used for testing, sends only 5 entries of both rc and discussion changes and sends daily overview")
parser.add_argument("--settings", default="settings.json", type=argparse.FileType(encoding='utf8'), help="provides a path to settings file (default ./settings.json)")
command_args, unknown = parser.parse_known_args()

