from src.configloader import settings
import logging

from src.migrations.utils import return_example_file

logger = logging.getLogger("rcgcdw.migrations.1.13.1.1")
base_file = return_example_file()
new_settings = settings.copy()


def run():
	if "event_appearance" not in settings:
		try:
			settings["event_appearance"] = {}
			struct = settings['appearance']['embed']
			for key, value in struct.items():
				settings["event_appearance"][key] = value
				settings["event_appearance"][key]["emoji"] = base_file["event_appearance"]
		except KeyError:
			logger.error("Failed to migrate appearance embed.")
	else:  # Don't do migrations
		return

