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
from typing import Union, Optional
from src.configloader import settings
logger = logging.getLogger("rcgcdw.i18n")
rcgcdw: Optional[Union[gettext.GNUTranslations, gettext.NullTranslations]] = None
discussion_formatters: Optional[Union[gettext.GNUTranslations, gettext.NullTranslations]] = None
rc: Optional[Union[gettext.GNUTranslations, gettext.NullTranslations]] = None
formatters_i18n: Optional[Union[gettext.GNUTranslations, gettext.NullTranslations]] = None
misc: Optional[Union[gettext.GNUTranslations, gettext.NullTranslations]] = None
redaction: Optional[Union[gettext.GNUTranslations, gettext.NullTranslations]] = None
# Setup translation


def python37_pgettext_backward_compatibility(context: str, string: str):
	"""Creates backward compatibility with Python 3.7 as pgettext has been introduced only in Python 3.8"""
	translation = formatters_i18n.gettext("{}\x04{}".format(context, string))
	if "\x04" in translation:  # gettext returned same message
		return string
	return translation


def load_languages():
	global rcgcdw, rc, formatters_i18n, misc, redaction
	try:
		if settings["lang"] != "en":
			rcgcdw = gettext.translation('rcgcdw', localedir='locale', languages=[settings["lang"]])
			rc = gettext.translation('rc', localedir='locale', languages=[settings["lang"]])
			formatters_i18n = gettext.translation('formatters', localedir='locale', languages=[settings["lang"]])
			misc = gettext.translation('misc', localedir='locale', languages=[settings["lang"]])
			redaction = gettext.translation('redaction', localedir='locale', languages=[settings["lang"]])
		else:
			rcgcdw, discussion_formatters, rc, formatters_i18n, misc, redaction = gettext.NullTranslations(), gettext.NullTranslations(), gettext.NullTranslations(), gettext.NullTranslations(), gettext.NullTranslations(), gettext.NullTranslations()
		formatters_i18n.pgettext = python37_pgettext_backward_compatibility
	except FileNotFoundError:
		logger.critical("No language files have been found. Make sure locale folder is located in the directory.")
		sys.exit(1)


load_languages()