#!/usr/bin/python
# -*- coding: utf-8 -*-

# Recent changes Goat compatible Discord webhook is a project for using a webhook as recent changes page from MediaWiki.
# Copyright (C) 2018 Frisk

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import json, time, sys, re

try:
	import requests
except ModuleNotFoundError:
	print("The requests module couldn't be found. Please install requests library using pip install requests.")
	sys.exit(0)

if "--help" in sys.argv:
	print("""Usage: python configbuilder.py [OPTIONS]
	
	Options:
	--basic - Prepares only the most basic settings necessary to run the script, leaves a lot of customization options on default
	--advanced - Prepares advanced settings with great range of customization
	--annoying - Asks for every single value available""")
	sys.exit(0)

def default_or_custom(answer, default):
	if answer == "":
		return default
	else:
		return answer

def yes_no(answer):
	if answer.lower() == "y":
		return True
	elif answer.lower() == "n":
		return False
	else:
		raise ValueError

print("Welcome in RcGcDw config builder! This script is still work in progress so beware! You can accept the default value if provided in the question by using Enter key without providing any other input.\nWARNING! Your current settings.json will be overwritten if you continue!")

try:  # load settings
	with open("../settings.json.example") as sfile:
		settings = json.load(sfile)
except FileNotFoundError:
	if yes_no(default_or_custom(input("Template config (settings.json.example) could not be found. Download the most recent stable one from master branch? (https://gitlab.com/piotrex43/RcGcDw/raw/master/settings.json.example)? (Y/n)"), "y")):
		settings = requests.get("https://gitlab.com/piotrex43/RcGcDw/raw/master/settings.json.example").json()

def basic():
	while True:
		if set_cooldown():
			break
	while True:
		if set_wiki():
			break
	while True:
		if set_lang():
			break
	while True:
		if set_webhook():
			break
	while True:
		if set_wikiname():
			break
	while True:
		if set_displaymode():
			break

def advanced():
	while True:
		if set_limit():
			break
	while True:
		if set_refetch_limit():
			break
	while True:
		if set_updown_messages():
			break
	if settings["show_updown_messages"]:
		while True:
			if set_downup_avatars():
				break
	while True:
		if set_ignored_events():
			break
	while True:
		if set_overview():
			break
	if settings["overview"]:
		while True:
			if set_overview_time():
				break
		while True:
			if set_empty_overview():
				break
	while True:
		if set_license_detection():
			break
	if settings["license_detection"]:
		while True:
			if set_license_detection_regex():
				break
		while True:
			if set_license_classification_regex():
				break
	while True:
		if set_login():
			break
	if settings["wiki_bot_login"]:
		while True:
			if set_password():
				break


def set_cooldown():
	option = default_or_custom(input("Interval for fetching recent changes in seconds (min. 10, default 30).\n"), 30)
	try:
		option = int(option)
		if option < 10:
			print("Please give a value higher than 9!")
			return False
		else:
			settings["cooldown"] = option
			return True
	except ValueError:
		print("Please give a valid number.")
		return False

def set_wiki():
	option = input("Please give the wiki you want to be monitored. (for example 'minecraft' or 'terraria-pl' are valid options)\n")
	if option.startswith("http"):
		regex = re.search(r"http(?:s|):\/\/(.*?)\.gamepedia.com", option)
		if regex.group(1):
			option = regex.group(1)
	print("Checking the wiki...")
	wiki_request = requests.get("https://{}.gamepedia.com".format(option), timeout=10, allow_redirects=False)  # TODO Actually check the API endpoint
	if wiki_request.status_code == 404 or wiki_request.status_code == 302:
		print("Wiki at https://{}.gamepedia.com does not exist, are you sure you have entered the wiki correctly?".format(option))
		return False
	else:
		settings["wiki"] = option
		return True

def set_lang():
	option = default_or_custom(input(
		"Please provide a language code for translation of the script. Translations available: en, de, ru, pt-br, fr, pl, uk. (default en)\n"), "en")
	if option in ["en", "de", "ru", "pt-br", "fr", "pl", "uk"]:
		settings["lang"] = option
		return True
	return False

def set_webhook():
	option = input(
		"Webhook URL is required. You can get it on Discord by following instructions on this page: https://support.discordapp.com/hc/en-us/articles/228383668-Intro-to-Webhooks\n")
	if option.startswith("https://discord.com/api/webhooks/") or option.startswith("https://discordapp.com/api/webhooks/"):
		test_webhook = requests.get(option)
		if test_webhook.status_code != 200:
			print("The webhook URL does not seem right. Reason: {}".format(test_webhook.json()["message"]))
			return False
		else:
			settings["webhookURL"] = option
			return True
	else:
		print("A Discord webhook URL should start with https://discord.com/api/webhooks/, are you sure it's the right URL?")
		return False

def set_wikiname():
	option = input("Please provide any wiki name for the wiki (can be whatever, but should be a full name of the wiki, for example \"Minecraft Wiki\")\n") # TODO Fetch the wiki yourself using api by default
	settings["wikiname"] = option
	return True

def set_displaymode():
	option = default_or_custom(input(
		"Please choose the display mode for the feed. More on how they look like on https://gitlab.com/piotrex43/RcGcDw/wikis/Presentation. Valid values: compact or embed. Default: embed\n"), "embed").lower()
	if option in ["embed", "compact"]:
		settings["appearance"]["mode"] = option
		return True
	print("Invalid mode selected!")
	return False

def set_limit():
	option = default_or_custom(input("Limit for amount of changes fetched every {} seconds. (default: 10, minimum: 1, the less active wiki is the lower the value should be)\n".format(settings["cooldown"])), 10)
	try:
		option = int(option)
		if option < 2:
			print("Please give a value higher than 1!")
			return False
		else:
			settings["limit"] = option
			return True
	except ValueError:
		print("Please give a valid number.")
		return False

def set_refetch_limit():
	option = default_or_custom(input("Limit for amount of changes fetched every time the script starts. (default: 28, minimum: {})\n".format(settings["limit"])), 28)
	try:
		option = int(option)
		if option < settings["limit"]:
			print("Please give a value higher than {}!".format(settings["limit"]))
			return False
		else:
			settings["limit"] = option
			return True
	except ValueError:
		print("Please give a valid number.")
		return False

def set_updown_messages():
	try:
		option = yes_no(default_or_custom(input("Should the script send messages when the wiki becomes unavailable? (Y/n)\n"), "y"))
		settings["show_updown_messages"] = option
		return True
	except ValueError:
		print("Response not valid, please use y (yes) or n (no)")
		return False

def set_downup_avatars():
	option = default_or_custom(input("Provide a link for a custom webhook avatar when the wiki goes DOWN. (default: no avatar)\n"), "")  #TODO Add a check for the image
	settings["avatars"]["connection_failed"] = option
	option = default_or_custom(
		input("Provide a link for a custom webhook avatar when the connection to the wiki is RESTORED. (default: no avatar)\n"),
		"")  # TODO Add a check for the image
	settings["avatars"]["connection_failed"] = option
	return True

def set_ignored_events():
	option = default_or_custom(
		input("Provide a list of entry types that are supposed to be ignored. Separate them using commas. Example: external, edit, upload/overwrite. (default: external)\n"), "external")  # TODO Add a check for the image
	entry_types = []
	for etype in option.split(","):
		entry_types.append(etype.strip())
	settings["ignored"] = entry_types
	return True

def set_overview():
	try:
		option = yes_no(default_or_custom(input("Should the script send daily overviews of the actions done on the wiki for past 24 hours? (y/N)\n"), "n"))
		settings["overview"] = option
		return True
	except ValueError:
		print("Response not valid, please use y (yes) or n (no)")
		return False

def set_overview_time():
	option = default_or_custom(input("At what time should the daily overviews be sent? (script uses local machine time, the format of the time should be HH:MM, default is 00:00)\n"), "00:00")
	check = re.match(r"^\d{2}:\d{2}$", option)
	if check is not None:
		settings["overview_time"] = option
		return True
	else:
		print("Response not valid, please enter a time in format HH:MM like for example 00:00 or 15:21!")
		return False

def set_empty_overview():
	try:
		option = yes_no(default_or_custom(input("Should the script send empty overviews in case nothing happens during the day? (y/N)\n"), "n"))
		settings["send_empty_overview"] = option
		return True
	except ValueError:
		print("Response not valid, please use y (yes) or n (no)")
		return False

def set_license_detection():
	try:
		option = yes_no(default_or_custom(input("Should the script detect licenses in the newly uploaded images? (Y/n)\n"), "y"))
		settings["license_detection"] = option
		return True
	except ValueError:
		print("Response not valid, please use y (yes) or n (no)")
		return False

def set_license_detection_regex():
	try:
		option = default_or_custom(input("Please provide regex for license detection (only to find it, the next step will be a regex to determine the type of the license). Default: \{\{(license|lizenz|licence|copyright)\n"), "\{\{(license|lizenz|licence|copyright)")
		re.compile(option)
		settings["license_regex_detect"] = option
		return True
	except re.error:
		print("Given regex expression could not be compiled. Please provide a proper regex expression in Python.")
		return False

def set_license_classification_regex():
	try:
		option = default_or_custom(input("Please provide regex for license classification where named capture group \"license\" is used as a license type for the image. Default: \{\{(license|lizenz|licence|copyright)(\ |\|)(?P<license>.*?)\}\}\n"), "\{\{(license|lizenz|licence|copyright)(\ |\|)(?P<license>.*?)\}\}")
		re.compile(option)
		settings["license_regex"] = option
		return True
	except re.error:
		print("Given regex expression could not be compiled. Please provide a proper regex expression in Python.")
		return False

def set_login():
	option = default_or_custom(input("You can provide bot credentials if you want the script to use higher limits than usual. If that's the case, please provide the login. If not, just skip this option \n"), "")
	settings["wiki_bot_login"] = option
	return True

def set_password():
	option = default_or_custom(input("Please give bot password now.\n"), "")
	settings["wiki_bot_password"] = option
	return True


try:
	basic()
	with open("settings.json", "w") as settings_file:
		settings_file.write(json.dumps(settings, indent=4))
	if "--advanced" in sys.argv:
		print("Basic part of the config has been completed. Starting the advanced part...")
		advanced()
	print("Responses has been saved! Your settings.json should be now valid and bot ready to run.")
except KeyboardInterrupt:
	if not yes_no(default_or_custom(input("\nSave the config before exiting? (y/N)"),"n")):
		sys.exit(0)
	else:
		with open("settings.json", "w") as settings_file:
			settings_file.write(json.dumps(settings, indent=4))