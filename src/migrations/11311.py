from src.configloader import settings, load_settings
import logging
import shutil
import time
import json
import sys

from src.migrations.utils import return_example_file

logger = logging.getLogger("rcgcdw.migrations.1.13.1.1")
new_settings = settings.copy()

def run():
	if "event_appearance" not in settings:
		logger.info("Running migration 1.13.1.1")
		base_file = return_example_file()
		if "event_appearance" not in base_file:  # if local base file is outdated, download from repo
			base_file = return_example_file(force=True)
		try:
			struct = settings['appearance']['embed']
			new_settings["event_appearance"] = {}
			keys = []
			for key, value in struct.items():
				if key not in ("show_edit_changes", "show_footer", "embed_images"):
					new_settings["event_appearance"][key] = value
					try:
						new_settings["event_appearance"][key]["emoji"] = base_file["event_appearance"][key]["emoji"]
					except KeyError:
						new_settings["event_appearance"][key]["emoji"] = ""
					keys.append(key)
			for item in keys:
				del new_settings['appearance']['embed'][item]
		except KeyError:
			logger.exception("Failed to migrate appearance embed.")
			sys.exit(1)
		shutil.copy("settings.json", "settings.json.{}.bak".format(int(time.time())))
		with open("settings.json", "w", encoding="utf-8") as new_write:
			new_write.write(json.dumps(new_settings, indent=4))
		load_settings()
		logger.info("Migration 1.13.1.1 has been successful.")
	else:
		logger.debug("Ignoring migration 1.13.1.1")


run()
