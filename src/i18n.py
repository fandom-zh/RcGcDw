import gettext, sys, logging
from src.configloader import settings
logger = logging.getLogger("rcgcdw.i18n")

# Setup translation

try:
	if settings["lang"] != "en":
		lang = gettext.translation('rcgcdw', localedir='locale', languages=[settings["lang"]])
		disc = gettext.translation('discussions', localedir='locale', languages=[settings["lang"]])
		misc = gettext.translation('misc', localedir='locale', languages=[settings["lang"]])
	else:
		lang, disc, misc = gettext.NullTranslations(), gettext.NullTranslations(), gettext.NullTranslations()
except FileNotFoundError:
	logger.critical("No language files have been found. Make sure locale folder is located in the directory.")
	sys.exit(1)

lang.install()
ngettext = lang.ngettext