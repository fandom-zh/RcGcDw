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
	else:
		rcgcdw, discussion_formatters, rc, rc_formatters, misc = gettext.NullTranslations(), gettext.NullTranslations(), gettext.NullTranslations(), gettext.NullTranslations(), gettext.NullTranslations()
except FileNotFoundError:
	logger.critical("No language files have been found. Make sure locale folder is located in the directory.")
	sys.exit(1)
