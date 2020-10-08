import re
import sys
import time
import logging
import requests
from bs4 import BeautifulSoup

from src.configloader import settings
from src.misc import WIKI_SCRIPT_PATH, WIKI_API_PATH, messagequeue, datafile, send_simple, safe_read, LinkParser
from src.exceptions import MWError
from src.session import session
from src.rc_formatters import compact_formatter, embed_formatter, compact_abuselog_formatter, embed_abuselog_formatter
from src.i18n import rc
from collections import OrderedDict

_ = rc.gettext

storage = datafile.data

logger = logging.getLogger("rcgcdw.rc")

supported_logs = ["protect/protect", "protect/modify", "protect/unprotect", "upload/overwrite", "upload/upload", "delete/delete", "delete/delete_redir", "delete/restore", "delete/revision", "delete/event", "import/upload", "import/interwiki", "merge/merge", "move/move", "move/move_redir", "protect/move_prot", "block/block", "block/unblock", "block/reblock", "rights/rights", "rights/autopromote", "abusefilter/modify", "abusefilter/create", "interwiki/iw_add", "interwiki/iw_edit", "interwiki/iw_delete", "curseprofile/comment-created", "curseprofile/comment-edited", "curseprofile/comment-deleted", "curseprofile/comment-purged", "curseprofile/profile-edited", "curseprofile/comment-replied", "contentmodel/change", "sprite/sprite", "sprite/sheet", "sprite/slice", "managetags/create", "managetags/delete", "managetags/activate", "managetags/deactivate", "tag/update", "cargo/createtable", "cargo/deletetable", "cargo/recreatetable", "cargo/replacetable", "upload/revert", "newusers/create", "newusers/autocreate", "newusers/create2", "newusers/byemail", "newusers/newusers", "managewiki/settings"]

# Set the proper formatter
if settings["appearance"]["mode"] == "embed":
	appearance_mode = embed_formatter
	abuselog_appearance_mode = embed_abuselog_formatter
elif settings["appearance"]["mode"] == "compact":
	appearance_mode = compact_formatter
	abuselog_appearance_mode = compact_abuselog_formatter
else:
	logger.critical("Unknown formatter!")
	sys.exit(1)


LinkParser = LinkParser()

class Recent_Changes_Class(object):
	"""Store verious data and functions related to wiki and fetching of Recent Changes"""
	def __init__(self):
		self.ids = []
		self.map_ips = {}
		self.recent_id = 0
		self.recent_abuse_id = 0
		self.downtimecredibility = 0
		self.last_downtime = 0
		self.tags = {}
		self.groups = {}
		self.streak = -1
		self.mw_messages = {}
		self.namespaces = None
		self.session = session
		self.logged_in = False
		if settings["limitrefetch"] != -1:
			self.file_id = storage["rcid"]
		else:
			self.file_id = 999999999  # such value won't cause trouble, and it will make sure no refetch happen

	@staticmethod
	def handle_mw_errors(request):
		if "errors" in request:
			logger.error(request["errors"])
			raise MWError
		return request

	def log_in(self):
		# session.cookies.clear()
		if '@' not in settings["wiki_bot_login"]:
			logger.error(
				"Please provide proper nickname for login from {wiki}Special:BotPasswords".format(
					wiki=WIKI_SCRIPT_PATH))
			return
		if len(settings["wiki_bot_password"]) != 32:
			logger.error(
				"Password seems incorrect. It should be 32 characters long! Grab it from {wiki}Special:BotPasswords".format(
					wiki=WIKI_SCRIPT_PATH))
			return
		logger.info("Trying to log in to {wiki}...".format(wiki=WIKI_SCRIPT_PATH))
		try:
			response = self.handle_mw_errors(
				self.session.post(WIKI_API_PATH,
				                  data={'action': 'query', 'format': 'json', 'utf8': '', 'meta': 'tokens',
				                        'type': 'login'}))
			response = self.handle_mw_errors(
				self.session.post(WIKI_API_PATH,
				                  data={'action': 'login', 'format': 'json', 'utf8': '',
				                        'lgname': settings["wiki_bot_login"],
				                        'lgpassword': settings["wiki_bot_password"],
				                        'lgtoken': response.json()['query']['tokens']['logintoken']}))
		except ValueError:
			logger.error("Logging in have not succeeded")
			return
		except MWError:
			logger.error("Logging in have not succeeded")
			return
		try:
			if response.json()['login']['result'] == "Success":
				logger.info("Successfully logged in")
				self.logged_in = True
			else:
				logger.error("Logging in have not succeeded")
		except:
			logger.error("Logging in have not succeeded")

	def add_cache(self, change):
		self.ids.append(change["rcid"])
		# self.recent_id = change["rcid"]
		if len(self.ids) > settings["limitrefetch"] + 5:
			self.ids.pop(0)

	def fetch(self, amount=settings["limit"]):
		messagequeue.resend_msgs()
		last_check = self.fetch_changes(amount=amount)
		# If the request succeeds the last_check will be the last rcid from recentchanges query
		if last_check is not None:
			self.recent_id = last_check
		# Assigns self.recent_id the last rcid if request succeeded, otherwise set the id from the file
		if settings["limitrefetch"] != -1 and self.recent_id != self.file_id and self.recent_id != 0:  # if saving to database is disabled, don't save the recent_id
			self.file_id = self.recent_id
			storage["rcid"] = self.recent_id
			datafile.save_datafile()
		logger.debug("Most recent rcid is: {}".format(self.recent_id))
		return self.recent_id

	def construct_params(self, amount):
		params = OrderedDict(action="query", format="json")
		params["list"] = "recentchanges|abuselog" if settings.get("show_abuselog", False) else "recentchanges"
		params["rcshow"] = "" if settings.get("show_bots", False) else "!bot"
		params["rcprop"] = "title|redirect|timestamp|ids|loginfo|parsedcomment|sizes|flags|tags|user"
		params["rclimit"] = amount
		params["rctype"] = "edit|new|log|external|categorize" if settings.get("show_added_categories", True) else "edit|new|log|external"
		if settings.get("show_abuselog", False):
			params["afllimit"] = amount
			params["aflprop"] = "ids|user|title|action|result|timestamp|hidden|revid|filter"
		return params

	def fetch_changes(self, amount, clean=False):
		"""Fetches the :amount: of changes from the wiki.
		Returns None on error and int of rcid of latest change if succeeded"""
		global logged_in
		if len(self.ids) == 0:
			logger.debug("ids is empty, triggering clean fetch")
			clean = True
		raw_changes = self.safe_request(WIKI_API_PATH, params=self.construct_params(amount))
		# action=query&format=json&list=recentchanges%7Cabuselog&rcprop=title%7Credirect%7Ctimestamp%7Cids%7Cloginfo%7Cparsedcomment%7Csizes%7Cflags%7Ctags%7Cuser&rcshow=!bot&rclimit=20&rctype=edit%7Cnew%7Clog%7Cexternal&afllimit=10&aflprop=ids%7Cuser%7Ctitle%7Caction%7Cresult%7Ctimestamp%7Chidden%7Crevid%7Cfilter
		if raw_changes:
			try:
				raw_changes = raw_changes.json()
				changes = raw_changes['query']['recentchanges']
				# {"batchcomplete":"","warnings":{"query":{"*":"Unrecognized value for parameter \"list\": abuselog."}}}
				changes.reverse()
				if "warnings" in raw_changes:
					warnings = raw_changes.get("warnings", {"query": {"*": ""}})
					if warnings["query"]["*"] == "Unrecognized value for parameter \"list\": abuselog.":
						settings["show_abuselog"] = False
						logger.warning("AbuseLog extension is not enabled on the wiki. Disabling the function...")
			except ValueError:
				logger.warning("ValueError in fetching changes")
				logger.warning("Changes URL:" + raw_changes.url)
				self.downtime_controller()
				return None
			except KeyError:
				logger.warning("Wiki returned %s" % (raw_changes))
				return None
			else:
				if self.downtimecredibility > 0:
					self.downtimecredibility -= 1
					if self.streak > -1:
						self.streak += 1
					if self.streak > 8:
						self.streak = -1
						send_simple("down_detector", _("Connection to {wiki} seems to be stable now.").format(wiki=settings["wikiname"]),
						     _("Connection status"), settings["avatars"]["connection_restored"])
				# In the first for loop we analize the categorize events and figure if we will need more changes to fetch
				# in order to cover all of the edits
				categorize_events = {}
				new_events = 0
				for change in changes:
					if not (change["rcid"] in self.ids or change["rcid"] < self.recent_id) and not clean:
						new_events += 1
						logger.debug(
							"New event: {}".format(change["rcid"]))
						if new_events == settings["limit"]:
							if amount < 500:
								# call the function again with max limit for more results, ignore the ones in this request
								logger.debug("There were too many new events, requesting max amount of events from the wiki.")
								return self.fetch(amount=5000 if self.logged_in else 500)
							else:
								logger.debug(
									"There were too many new events, but the limit was high enough we don't care anymore about fetching them all.")
					if change["type"] == "categorize":
						if "commenthidden" not in change:
							if len(recent_changes.mw_messages.keys()) > 0:
								cat_title = change["title"].split(':', 1)[1]
								# I so much hate this, blame Markus for making me do this
								if change["revid"] not in categorize_events:
									categorize_events[change["revid"]] = {"new": set(), "removed": set()}
								comment_to_match = re.sub(r'<.*?a>', '', change["parsedcomment"])
								if recent_changes.mw_messages["recentchanges-page-added-to-category"] in comment_to_match or recent_changes.mw_messages["recentchanges-page-added-to-category-bundled"] in comment_to_match:
									categorize_events[change["revid"]]["new"].add(cat_title)
									logger.debug("Matched {} to added category for {}".format(cat_title, change["revid"]))
								elif recent_changes.mw_messages["recentchanges-page-removed-from-category"] in comment_to_match or recent_changes.mw_messages["recentchanges-page-removed-from-category-bundled"] in comment_to_match:
									categorize_events[change["revid"]]["removed"].add(cat_title)
									logger.debug("Matched {} to removed category for {}".format(cat_title, change["revid"]))
								else:
									logger.debug("Unknown match for category change with messages {}, {}, {}, {} and comment_to_match {}".format(recent_changes.mw_messages["recentchanges-page-added-to-category"], recent_changes.mw_messages["recentchanges-page-removed-from-category"], recent_changes.mw_messages["recentchanges-page-removed-from-category-bundled"], recent_changes.mw_messages["recentchanges-page-added-to-category-bundled"], comment_to_match))
							else:
								logger.warning("Init information not available, could not read category information. Please restart the bot.")
						else:
							logger.debug("Log entry got suppressed, ignoring entry.")
				# if change["revid"] in categorize_events:
						# 	categorize_events[change["revid"]].append(cat_title)
						# else:
						# 	logger.debug("New category '{}' for {}".format(cat_title, change["revid"]))
						# 	categorize_events[change["revid"]] = {cat_title: }
				for change in changes:
					if change["rcid"] in self.ids or change["rcid"] < self.recent_id:
						logger.debug("Change ({}) is in ids or is lower than recent_id {}".format(change["rcid"],
						                                                                           self.recent_id))
						continue
					logger.debug(self.ids)
					logger.debug(self.recent_id)
					self.add_cache(change)
					if clean and not (self.recent_id == 0 and change["rcid"] > self.file_id):
						logger.debug("Rejected {val}".format(val=change["rcid"]))
						continue
					essential_info(change, categorize_events.get(change.get("revid"), None))
				if "abuselog" in raw_changes["query"]:
					abuse_log = raw_changes['query']['recentchanges']
					abuse_log.reverse()
					for entry in abuse_log:
						abuselog_processing(entry, self)
				return change["rcid"]

	def safe_request(self, url, params=None):
		try:
			if params:
				request = self.session.get(url, params=params, timeout=10, allow_redirects=False)
			else:
				request = self.session.get(url, timeout=10, allow_redirects=False)
		except requests.exceptions.Timeout:
			logger.warning("Reached timeout error for request on link {url}".format(url=url))
			self.downtime_controller()
			return None
		except requests.exceptions.ConnectionError:
			logger.warning("Reached connection error for request on link {url}".format(url=url))
			self.downtime_controller()
			return None
		except requests.exceptions.ChunkedEncodingError:
			logger.warning("Detected faulty response from the web server for request on link {url}".format(url=url))
			self.downtime_controller()
			return None
		else:
			if 499 < request.status_code < 600:
				self.downtime_controller()
				return None
			elif request.status_code == 302:
				logger.critical("Redirect detected! Either the wiki given in the script settings (wiki field) is incorrect/the wiki got removed or Gamepedia is giving us the false value. Please provide the real URL to the wiki, current URL redirects to {}".format(request.next.url))
				sys.exit(0)
			return request

	def check_connection(self, looped=False):
		online = 0
		for website in ["https://google.com", "https://instagram.com", "https://steamcommunity.com"]:
			try:
				requests.get(website, timeout=10)
				online += 1
			except requests.exceptions.ConnectionError:
				pass
			except requests.exceptions.Timeout:
				pass
		if online < 1:
			logger.error("Failure when checking Internet connection at {time}".format(
				time=time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime())))
			self.downtimecredibility = 0
			if not looped:
				while 1:  # recursed loop, check for connection (every 10 seconds) as long as three services are down, don't do anything else
					if self.check_connection(looped=True):
						recent_changes.fetch(amount=settings["limitrefetch"])
						break
					time.sleep(10)
			return False
		return True

	def downtime_controller(self):
		if not settings["show_updown_messages"]:
			return
		if self.streak > -1:  # reset the streak of successful connections when bad one happens
			self.streak = 0
		if self.downtimecredibility < 60:
			self.downtimecredibility += 15
		else:
			if (
					time.time() - self.last_downtime) > 1800 and self.check_connection():  # check if last downtime happened within 30 minutes, if yes, don't send a message
				send_simple("down_detector", _("{wiki} seems to be down or unreachable.").format(wiki=settings["wikiname"]),
				     _("Connection status"), settings["avatars"]["connection_failed"])
				self.last_downtime = time.time()
				self.streak = 0

	def clear_cache(self):
		self.map_ips = {}

	def init_info(self):
		startup_info = safe_read(self.safe_request(
			"{wiki}?action=query&format=json&uselang=content&list=tags&meta=allmessages%7Csiteinfo&utf8=1&tglimit=max&tgprop=displayname&ammessages=recentchanges-page-added-to-category%7Crecentchanges-page-removed-from-category%7Crecentchanges-page-added-to-category-bundled%7Crecentchanges-page-removed-from-category-bundled&amenableparser=1&amincludelocal=1&siprop=namespaces".format(
				wiki=WIKI_API_PATH)), "query")
		if startup_info:
			if "tags" in startup_info and "allmessages" in startup_info:
				for tag in startup_info["tags"]:
					try:
						self.tags[tag["name"]] = (BeautifulSoup(tag["displayname"], "lxml")).get_text()
					except KeyError:
						self.tags[tag["name"]] = None  # Tags with no display name are hidden and should not appear on RC as well
				for message in startup_info["allmessages"]:
					if not "missing" in message:  # ignore missing strings
						self.mw_messages[message["name"]] = message["*"]
					else:
						logging.warning("Could not fetch the MW message translation for: {}".format(message["name"]))
				for key, message in self.mw_messages.items():
					if key.startswith("recentchanges-page-"):
						self.mw_messages[key] = re.sub(r'\[\[.*?\]\]', '', message)
				self.namespaces = startup_info["namespaces"]
				logger.info("Gathered information about the tags and interface messages.")
			else:
				logger.warning("Could not retrieve initial wiki information. Some features may not work correctly!")
				logger.debug(startup_info)
		else:
			logger.error("Could not retrieve initial wiki information. Possibly internet connection issue?")

	def pull_comment(self, comment_id):
		try:
			comment = self.handle_mw_errors(self.safe_request(
				"{wiki}?action=comment&do=getRaw&comment_id={comment}&format=json".format(wiki=WIKI_API_PATH,
				                                                                          comment=comment_id)).json())[
				"text"]
			logger.debug("Got the following comment from the API: {}".format(comment))
		except MWError:
			pass
		except (TypeError, AttributeError):
			logger.exception("Could not resolve the comment text.")
		except KeyError:
			logger.exception("CurseProfile extension API did not respond with a valid comment content.")
		else:
			if len(comment) > 1000:
				comment = comment[0:1000] + "…"
			return comment
		return ""


recent_changes = Recent_Changes_Class()

def essential_info(change, changed_categories):
	"""Prepares essential information for both embed and compact message format."""
	logger.debug(change)
	if ("actionhidden" in change or "suppressed" in change) and "suppressed" not in settings["ignored"]:  # if event is hidden using suppression
		appearance_mode("suppressed", change, "", changed_categories, recent_changes)
		return
	if "commenthidden" not in change:
		LinkParser.feed(change["parsedcomment"])
		parsed_comment = LinkParser.new_string
		LinkParser.new_string = ""
		parsed_comment = re.sub(r"(`|_|\*|~|{|}|\|\|)", "\\\\\\1", parsed_comment, 0)
	else:
		parsed_comment = _("~~hidden~~")
	if not parsed_comment:
		parsed_comment = None
	if change["type"] in ["edit", "new"]:
		logger.debug("List of categories in essential_info: {}".format(changed_categories))
		if "userhidden" in change:
			change["user"] = _("hidden")
		identification_string = change["type"]
	elif change["type"] == "log":
		identification_string = "{logtype}/{logaction}".format(logtype=change["logtype"], logaction=change["logaction"])
		if identification_string not in supported_logs:
			logger.warning(
				"This event is not implemented in the script. Please make an issue on the tracker attaching the following info: wiki url, time, and this information: {}".format(
					change))
			return
	elif change["type"] == "categorize":
		return
	else:
		logger.warning("This event is not implemented in the script. Please make an issue on the tracker attaching the following info: wiki url, time, and this information: {}".format(change))
		return
	if identification_string in settings["ignored"]:
		return
	appearance_mode(identification_string, change, parsed_comment, changed_categories, recent_changes)

def abuselog_processing(entry, recent_changes):
	abuselog_appearance_mode(entry, recent_changes)