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

from src.api.hook import pre_hook, post_hook


@pre_hook
def example_pre_hook(context, change):
    if context.event == "edit":
        print("I'm an edit with {} bytes changed!".format(change.get("newlen", 0) - change.get("oldlen", 0)))


@post_hook
def example_post_hook(message, metadata, context, change):
    print("Our Discord message looks as follows: ")
    print(message)
