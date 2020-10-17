import json, sys, logging

try:  # load settings
	with open("settings.json") as sfile:
		settings = json.load(sfile)
		if settings["limitrefetch"] < settings["limit"] and settings["limitrefetch"] != -1:
			settings["limitrefetch"] = settings["limit"]
		if "user-agent" in settings["header"]:
			settings["header"]["user-agent"] = settings["header"]["user-agent"].format(version="1.13")  # set the version in the useragent
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
