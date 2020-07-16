import gettext, sys, logging
from src.configloader import settings
logger = logging.getLogger("rcgcdw.i18n")

# Setup translation

try:
	lang = gettext.translation('rcgcdw', localedir='locale', languages=[settings["lang"]])
	disc = gettext.translation('discussions', localedir='locale', languages=[settings["lang"]])
except FileNotFoundError:
	logger.critical("No language files have been found. Make sure locale folder is located in the directory.")
	sys.exit(1)

lang.install()
ngettext = lang.ngettext