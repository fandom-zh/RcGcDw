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

import json
import logging
import sys
from src.argparser import command_args
global settings


def load_settings():
	global settings
	try:  # load settings
		command_args.settings.seek(0)
		settings = json.load(command_args.settings)
		if settings["limitrefetch"] < settings["limit"] and settings["limitrefetch"] != -1:
			settings["limitrefetch"] = settings["limit"]
		if "user-agent" in settings["header"]:
			settings["header"]["user-agent"] = settings["header"]["user-agent"].format(version="1.15.0.2")  # set the version in the useragent
	except FileNotFoundError:
		logging.critical("No config file could be found. Please make sure settings.json is in the directory.")
		sys.exit(1)
	# Set the cooldown to 15 seconds if it's a wiki farm like Fandom or Gamepedia and the cooldown is even lower than that.
	# Look, it's unreasonable to have even higher refresh rate than that, seriously. Setting it even lower can cause issues
	# for all users of the script for high usage of farm's servers. So please, do not remove this code unless you absolutely
	# know what you are doing <3
	if any(("fandom.com" in settings["wiki_url"], "gamepedia.com" in settings["wiki_url"])):
		if settings["cooldown"] < 15:
			settings["cooldown"] = 15
	if settings["fandom_discussions"]["cooldown"] < 15:
		settings["fandom_discussions"]["cooldown"] = 15


load_settings()

