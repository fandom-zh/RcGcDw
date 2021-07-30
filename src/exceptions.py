# This file is part of Recent changes Goat compatible Discord webhook (RcGcDw).

# RcGcDw is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# RcGcDw is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with RcGcDw.  If not, see <http://www.gnu.org/licenses/>.


class MWError(Exception):
	pass


class ArticleCommentError(Exception):
	pass


class FormatterBreaksAPISpec(Exception):
	def __init__(self, field):
		self.message = f"Formatter doesn't specify {field}!"
		super().__init__(self.message)


class ServerError(Exception):
	"""Exception for when a request fails because of Server error"""
	pass

class NoFormatter(Exception):
	"""Exception to throw when there are no formatters"""
	pass


class ClientError(Exception):
	"""Exception for when a request failes because of Client error"""

	def __init__(self, request):
		self.message = f"Client have made wrong request! {request.status_code}: {request.reason}. {request.text}"
		super().__init__(self.message)


class BadRequest(Exception):
	"""When type of parameter given to request making method is invalid"""
	def __init__(self, object_type):
		self.message = f"params must be either a strong or OrderedDict object, not {type(object_type)}!"
		super().__init__(self.message)


class MediaWikiError(Exception):
	"""When MediaWiki responds with an error"""
	def __init__(self, errors):
		self.message = f"MediaWiki returned the following errors: {errors}!"
		super().__init__(self.message)

