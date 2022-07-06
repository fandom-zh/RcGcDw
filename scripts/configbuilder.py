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

import json, time, sys, re, shutil
from urllib.parse import urlunparse, urlparse
from pprint import pprint

fandom_websites = ("fandom.com", "wikia.org")
new_issue_url = "https://gitlab.com/piotrex43/RcGcDw/-/issues/new"

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

def trap(method):
	while True:
		if method():
			break

class BasicSettings:
	def __init__(self):
		self.site_name = None
		method_tuple = (self.set_cooldown, self.set_wiki, self.set_discussion, self.set_lang, self.set_webhook, self.set_displaymode, self.set_wikiname)
		for method in method_tuple:
			trap(method)


	def prepare_paths(self, path):
		global WIKI_SCRIPT_PATH
		"""Set the URL paths for article namespace and script namespace
		WIKI_SCRIPT_PATH will be: WIKI_DOMAIN/"""

		def quick_try_url(url):
			"""Quickly test if URL is the proper script path,
			False if it appears invalid
			dictionary when it appears valid"""
			try:
				request = requests.get(url, timeout=5)
				if request.status_code == requests.codes.ok:
					if request.json()["query"]["general"] is not None:
						return request.json()["query"]["general"]
				return False
			except (KeyError, requests.exceptions.ConnectionError):
				return False
			except ValueError:
				return False

		parsed_url = urlparse(path)
		for url_scheme in (path, path.split("wiki")[0], urlunparse(
				(*parsed_url[0:2], "", "", "", ""))):  # check different combinations, it's supposed to be idiot-proof
			print("Checking {}...".format(url_scheme))
			tested = quick_try_url(url_scheme + "/api.php?action=query&format=json&meta=siteinfo")
			if tested:
				url = urlunparse((*parsed_url[0:2], "", "", "", "")) + tested["scriptpath"] + "/"
				self.site_name = tested["sitename"]
				print("Found {}, setting URL in the settings to {}".format(tested["sitename"], url))
				return url
		else:
			print(
				"Could not verify wikis paths. Please make sure you have given the proper wiki URLs in settings.json ({path} should be script path to your wiki) and your Internet connection is working.".format(
					path=path))

	@staticmethod
	def set_cooldown():
		option = default_or_custom(input("Interval for fetching recent changes in seconds (min. 30, default 60).\n"),
		                           60)
		try:
			option = int(option)
			if option < 29:
				print("Please give a value higher than 30!")
				return False
			else:
				settings["cooldown"] = option
				return True
		except ValueError:
			print("Please give a valid number.")


	def set_wiki(self):
		option = input(
			"Please give the wiki URL to be monitored. Can be any link to a script path of the MediaWiki wiki.)\n")
		path = self.prepare_paths(option)
		if path:
			settings["wiki_url"] = path
			return True
		print("Couldn't find a MediaWiki wiki under given URL.")

	@staticmethod
	def set_discussion():
		if urlparse(settings["wiki"]).netloc in fandom_websites:
			settings["fandom_discussions"]["enabled"] = yes_no(default_or_custom(input("Would you like to have discussions feed enabled for the wiki you previously specified? (available only for Fandom wikis)"), "n"))
			if settings["fandom_discussions"]["enabled"]:
				print("Retrieving necessary information from Fandom servers...")
				response = requests.get('https://community.fandom.com/api/v1/Wikis/ByString?includeDomain=true&limit=10&string={wikidomain}&format=json&cache={cache}'.format(wikidomain="".join(urlparse(settings["wiki"])[1:]), cache=time.time()))
				try:
					settings["fandom_discussions"]["wiki_id"] = int(response.json()["items"][0]["id"])
					settings["fandom_discussions"]["wiki_url"] = settings["wiki"]
				except KeyError:
					print("Could not setup the discussions, please report the issue on the issue tracker at {tracker} with the following information:".format(tracker="https://gitlab.com/piotrex43/RcGcDw/-/issues/new"))
					pprint(response.json())
				except ValueError:
					print("Could not setup the discussions, please report the issue on the issue tracker at {tracker} with the following information:".format(tracker="https://gitlab.com/piotrex43/RcGcDw/-/issues/new"))
					print(response)
					print('https://community.fandom.com/api/v1/Wikis/ByString?includeDomain=true&limit=10&string={wikidomain}&format=json&cache={cache}'.format(wikidomain="".join(urlparse(settings["wiki"])[1:]), cache=time.time()))
		return True

	@staticmethod
	def set_lang():
		option = default_or_custom(input(
			"Please provide a language code for translation of the script. Translations available: en, de, ru, pt-br, fr, pl, uk. zh-hant (default en)\n"),
			"en")
		if option in ["en", "de", "ru", "pt-br", "fr", "pl", "uk", "zh-hant"]:
			settings["lang"] = option
			return True
		return False

	@staticmethod
	def set_webhook():
		option = input(
			"Webhook URL is required. You can get it on Discord by following instructions on this page: https://support.discordapp.com/hc/en-us/articles/228383668-Intro-to-Webhooks\n")
		if option.startswith("https://discord.com/api/webhooks/") or option.startswith(
				"https://discordapp.com/api/webhooks/"):
			print("Checking webhook validity...")
			test_webhook = requests.get(option, timeout=10.0)
			if test_webhook.status_code != 200:
				print("The webhook URL does not seem right. Reason: {}".format(test_webhook.json()["message"]))
				return False
			else:
				settings["webhookURL"] = option
				return True
		else:
			print(
				"A Discord webhook URL should start with https://discord.com/api/webhooks/, are you sure it's the right URL?")
			return False


	def set_wikiname(self):
		option = default_or_custom(input(
			"Please provide any wiki name for the wiki (can be whatever, but should be a full name of the wiki, for example \"Minecraft Wiki\") otherwise it will be {}\n".format(self.site_name)), self.site_name)  # TODO Fetch the wiki yourself using api by default
		settings["wikiname"] = option
		return True


	@staticmethod
	def set_displaymode():
		option = default_or_custom(input(
			"Please choose the display mode for the feed. More on how they look like on https://gitlab.com/piotrex43/RcGcDw/wikis/Presentation. Valid values: compact or embed. Default: embed\n"), "embed").lower()
		if option in ["embed", "compact"]:
			settings["appearance"]["mode"] = option
			return True
		print("Invalid mode given! (can be embed or compact, {} given)".format(option))
		return False


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
	with open("../settings.json.example", encoding="utf-8") as sfile:
		settings = json.load(sfile)
except FileNotFoundError:
	if yes_no(default_or_custom(input("Template config (settings.json.example) could not be found. Download the most recent stable one from master branch? (https://gitlab.com/piotrex43/RcGcDw/raw/master/settings.json.example)? (Y/n)"), "y")):
		settings = requests.get("https://gitlab.com/piotrex43/RcGcDw/raw/master/settings.json.example").json()

class AdvancedSettings:
	def __init__(self):
		self.session = requests.session()
		method_tuple = (self.set_limit, self.set_start_refetch_limit, self.set_uptime_messages, self.set_uptime_avatars,
		                self.set_ignored_events, self.set_overviews, self.set_overview_time, self.set_empty_overview,
		                self.set_license_detection, self.set_license_detection_regex, self.set_license_classification_regex,
		                self.set_login_details, self.set_login_password)
		for method in method_tuple:
			trap(method)

	def log_in(self, login, password):
		print("Trying to log in to {wiki}...".format(wiki=settings["wiki_url"]))

		try:
			response = self.session.post(settings["wiki_url"],
				                  data={'action': 'query', 'format': 'json', 'utf8': '', 'meta': 'tokens',
				                        'type': 'login'})
			response = self.session.post(settings["wiki_url"],
				                  data={'action': 'login', 'format': 'json', 'utf8': '',
				                        'lgname': login,
				                        'lgpassword': password,
				                        'lgtoken': response.json()['query']['tokens']['logintoken']})
		except ValueError:
			print("Logging in have not succeeded")
			return
		try:
			if response.json()['login']['result'] == "Success":
				print("Successfully logged in")
				return True
			else:
				print("Logging in have not succeeded")
		except:
			print("Logging in have not succeeded")

	@staticmethod
	def set_limit():
		option = default_or_custom(input(
			"Limit for amount of changes fetched every {} seconds. (default: 10, minimum: 1, the less active wiki is the lower the value should be)\n".format(
				settings["cooldown"])), 10)
		try:
			option = int(option)
			if option < 2:
				print("Please give a value higher than 1!")
			else:
				settings["limit"] = option
				return True
		except ValueError:
			print("Please give a valid number.")

	@staticmethod
	def set_start_refetch_limit():
		option = default_or_custom(input(
			"Limit for amount of changes fetched every time the script starts. (default: 28, minimum: {})\n".format(
				settings["limit"])), 28)
		try:
			option = int(option)
			if option < settings["limit"]:
				print("Please give a value higher than {}!".format(settings["limit"]))
			else:
				settings["limitrefetch"] = option
				return True
		except ValueError:
			print("Please give a valid number.")

	@staticmethod
	def set_uptime_messages():
		try:
			option = yes_no(
				default_or_custom(input("Should the script send messages when the wiki becomes unavailable? (Y/n)\n"),
				                  "y"))
			settings["show_updown_messages"] = option
			return True
		except ValueError:
			print("Response not valid, please use y (yes) or n (no)")

	@staticmethod
	def set_uptime_avatars():
		if settings["show_updown_messages"]:
			option = default_or_custom(
				input("Provide a link for a custom webhook avatar when the wiki goes DOWN. (default: no avatar)\n"),
				"")
			try:
				if option:
					response = requests.head(option, timeout=10.0)
					if response.headers.get('content-type', "none") not in ('image/png', 'image/jpg', 'image/jpeg', 'image/webp', 'image/gif'):
						print("The images under URL is not in the proper format. Accepted formats are: png, jpg, jpeg, webp, gif, detected: {}".format(response.headers.get('content-type', "none")))
						return False
			except:
				raise
			settings["avatars"]["connection_failed"] = option
			option = default_or_custom(
				input(
					"Provide a link for a custom webhook avatar when the connection to the wiki is RESTORED. (default: no avatar)\n"),
				"")
			try:
				if option:
					response = requests.head(option, timeout=10.0)
					if response.headers.get('content-type', "none") not in ('image/png', 'image/jpg', 'image/jpeg', 'image/webp', 'image/gif'):
						print("The images under URL is not in the proper format. Accepted formats are: png, jpg, jpeg, webp, gif, detected: {}".format(response.headers.get('content-type', "none")))
						return False
			except:
				raise
			settings["avatars"]["connection_restored"] = option
			return True
		else:
			return True

	@staticmethod
	def set_ignored_events():
		supported_logs = ["protect/protect", "protect/modify", "protect/unprotect", "upload/overwrite", "upload/upload", "delete/delete", "delete/delete_redir", "delete/restore", "delete/revision", "delete/event", "import/upload", "import/interwiki", "merge/merge", "move/move", "move/move_redir", "protect/move_prot", "block/block", "block/unblock", "block/reblock", "rights/rights", "rights/autopromote", "abusefilter/modify", "abusefilter/create", "interwiki/iw_add", "interwiki/iw_edit", "interwiki/iw_delete", "curseprofile/comment-created", "curseprofile/comment-edited", "curseprofile/comment-deleted", "curseprofile/comment-purged", "curseprofile/profile-edited", "curseprofile/comment-replied", "contentmodel/change", "sprite/sprite", "sprite/sheet", "sprite/slice", "managetags/create", "managetags/delete", "managetags/activate", "managetags/deactivate", "cargo/createtable", "cargo/deletetable", "cargo/recreatetable", "cargo/replacetable", "upload/revert", "newusers/create", "newusers/autocreate", "newusers/create2", "newusers/byemail", "newusers/newusers", "newusers/reclaim", "edit", "new", "external"]
		option = default_or_custom(
			input(
				"Provide a list of entry types that are supposed to be ignored. Separate them using commas. Example: external, edit, upload/overwrite. (default: external)\n"),
			"external")
		entry_types = []
		for etype in option.split(","):
			if etype.strip() in supported_logs:
				entry_types.append(etype.strip())
			else:
				print("Type \"{}\" couldn't be added as it's not supported.".format(etype.strip()))
		try:
			if yes_no(default_or_custom(input("Accept {} as ignored events? (Y/n)".format(", ".join(entry_types))), "y")):
				settings["ignored"] = entry_types
				return True
		except ValueError:
			print("Response not valid, please use y (yes) or n (no)")

	@staticmethod
	def set_overviews():
		try:
			option = yes_no(default_or_custom(input(
				"Should the script send daily overviews of the actions done on the wiki for past 24 hours? (y/N)\n"),
			                                  "n"))
			settings["overview"] = option
			return True
		except ValueError:
			print("Response not valid, please use y (yes) or n (no)")

	@staticmethod
	def set_overview_time():
		if settings["overview"]:
			option = default_or_custom(input(
				"At what time should the daily overviews be sent? (script uses local machine time, the format of the time should be HH:MM, default is 00:00)\n"),
			                           "00:00")
			check = re.match(r"^\d{2}:\d{2}$", option)
			if check is not None:
				settings["overview_time"] = option
				return True
			else:
				print("Response not valid, please enter a time in format HH:MM like for example 00:00 or 15:21!")
		else:
			return True

	@staticmethod
	def set_empty_overview():
		try:
			option = yes_no(default_or_custom(
				input("Should the script send empty overviews in case nothing happens during the day? (y/N)\n"), "n"))
			settings["send_empty_overview"] = option
			return True
		except ValueError:
			print("Response not valid, please use y (yes) or n (no)")

	@staticmethod
	def set_license_detection():
		try:
			option = yes_no(
				default_or_custom(input("Should the script detect licenses in the newly uploaded images? (Y/n)\n"),
				                  "y"))
			settings["license_detection"] = option
			return True
		except ValueError:
			print("Response not valid, please use y (yes) or n (no)")

	@staticmethod
	def set_license_detection_regex():
		if settings["license_detection"]:
			try:
				option = default_or_custom(input(
					"Please provide regex (in Python format) for license detection (only to find it, the next step will be a regex to determine the type of the license). Default: \{\{(license|lizenz|licence|copyright)\n"),
				                           "\{\{(license|lizenz|licence|copyright)")
				re.compile(option)
				settings["license_regex_detect"] = option
				return True
			except re.error:
				print("Given regex expression could not be compiled. Please provide a proper regex expression in Python.")
				return False
		else:
			return True

	@staticmethod
	def set_license_classification_regex():
		if settings["license_detection"]:
			try:
				option = default_or_custom(input(
					"Please provide regex for license classification where named capture group \"license\" is used as a license type for the image. Default: \{\{(license|lizenz|licence|copyright)(\ |\|)(?P<license>.*?)\}\}\n"),
				                           "\{\{(license|lizenz|licence|copyright)(\ |\|)(?P<license>.*?)\}\}")
				re.compile(option)
				settings["license_regex"] = option
				return True
			except re.error:
				print(
					"Given regex expression could not be compiled. Please provide a proper regex expression in Python.")
				return False
		else:
			return True

	@staticmethod
	def set_login_details():
		option = default_or_custom(input(
			"You can provide bot credentials if you want the script to use higher limits than usual. If that's the case, please provide the login from Special:BotPasswords. If not, just hit Enter/return \n"),
		                           "")
		if "@" not in option:
			print("Please provide proper nickname for login from {wiki}Special:BotPasswords".format(
				wiki=settings["wiki_url"]))
			return False
		settings["wiki_bot_login"] = option
		return True

	def set_login_password(self):
		if settings["wiki_bot_login"]:
			option = default_or_custom(input("Please give bot password now, empty to cancel.\n"), "")
			if len(option) != 32 and len(option) != 0:
				print("Password seems incorrect. It should be 32 characters long! Grab it from {wiki}Special:BotPasswords".format(
						wiki=settings["wiki_url"]))
				return False
			if option == "":
				print("Logging in function has been disabled.")
				settings["wiki_bot_login"] = ""
				settings["wiki_bot_password"] = ""
				return True
			print("Trying the credentials...")
			self.log_in(settings["wiki_bot_login"], option)
			settings["wiki_bot_password"] = option
			print("Gathering data...")
			try:
				response = self.session.get(settings["wiki_url"]+"api.php?action=query&format=json&meta=userinfo&uiprop=rights", timeout=10.0)
			except:
				print("Could not fetch information about rights, skipping limit checks...")
				response = None
			if response:
				try:
					rights = response.json()["query"]["userinfo"]["rights"]
					if "apihighlimits" in rights:
						if settings["limit"] > 5000:
							print("Setting limit to 5000 as it's max we can do...")
							settings["limit"] = 5000
						if settings["limitrefetch"] > 5000:
							print("Setting limitrefetch to 5000 as it's max we can do...")
							settings["limitrefetch"] = 5000
					else:
						print("Credentials don't allow us to fetch more than 500 events.")
						if settings["limit"] > 500:
							print("Setting limit to 500 as it's max we can do...")
							settings["limit"] = 500
						if settings["limitrefetch"] > 500:
							print("Setting limitrefetch to 500 as it's max we can do...")
							settings["limitrefetch"] = 500
				except (ValueError, KeyError):
					print("Could not fetch information about rights, skipping limit checks...")
			return True


try:
	BasicSettings()
	shutil.copy("settings.json", "settings.json.bak")
	with open("settings.json", "w", encoding="utf-8") as settings_file:
		settings_file.write(json.dumps(settings, indent=4))
	if "--advanced" in sys.argv:
		print("Basic part of the config has been completed. Starting the advanced part...")
		AdvancedSettings()
	print("Responses has been saved! Your settings.json should be now valid and bot ready to run.")
except KeyboardInterrupt:
	if not yes_no(default_or_custom(input("\nSave the config before exiting? (y/N)"),"n")):
		sys.exit(0)
	else:
		with open("settings.json", "w", encoding="utf-8") as settings_file:
			settings_file.write(json.dumps(settings, indent=4))
