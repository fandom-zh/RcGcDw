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

import src.api.hooks


def pre_hook(func):
	"""
	Decorator to register a pre hook and return a function

	:return: func
	"""
	src.api.hooks.pre_hooks.append(func)
	return func


def post_hook(func):
	"""
	Decorator to register a post hook and return a function

	:return: func
	"""
	src.api.hooks.post_hooks.append(func)
	return func
