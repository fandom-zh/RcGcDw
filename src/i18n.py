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

import gettext, sys, logging
from src.configloader import settings
logger = logging.getLogger("rcgcdw.i18n")

# Setup translation

try:
	if settings["lang"] != "en":
		rcgcdw = gettext.translation('rcgcdw', localedir='locale', languages=[settings["lang"]])
		discussion_formatters = gettext.translation('discussion_formatters', localedir='locale', languages=[settings["lang"]])
		rc = gettext.translation('rc', localedir='locale', languages=[settings["lang"]])
		rc_formatters = gettext.translation('rc_formatters', localedir='locale', languages=[settings["lang"]])
		misc = gettext.translation('misc', localedir='locale', languages=[settings["lang"]])
		redaction = gettext.translation('redaction', localedir='locale', languages=[settings["lang"]])
	else:
		rcgcdw, discussion_formatters, rc, rc_formatters, misc, redaction = gettext.NullTranslations(), gettext.NullTranslations(), gettext.NullTranslations(), gettext.NullTranslations(), gettext.NullTranslations(), gettext.NullTranslations()
except FileNotFoundError:
	logger.critical("No language files have been found. Make sure locale folder is located in the directory.")
	sys.exit(1)
