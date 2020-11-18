import re
import sys
import time
import logging
import requests
from bs4 import BeautifulSoup

from src.configloader import settings
from src.misc import WIKI_SCRIPT_PATH, WIKI_API_PATH, datafile, send_simple, safe_read, LinkParser, AUTO_SUPPRESSION_ENABLED
from src.discord.queue import messagequeue
from src.exceptions import MWError
from src.session import session
from src.rc_formatters import compact_formatter, embed_formatter, compact_abuselog_formatter, embed_abuselog_formatter
from src.i18n import rc
from collections import OrderedDict

_ = rc.gettext

storage = datafile

logger = logging.getLogger("rcgcdw.rc")

supported_logs = {"protect/protect", "protect/modify", "protect/unprotect", "upload/overwrite", "upload/upload",
                  "delete/delete", "delete/delete_redir", "delete/restore", "delete/revision", "delete/event",
                  "import/upload", "import/interwiki", "merge/merge", "move/move", "move/move_redir",
                  "protect/move_prot", "block/block", "block/unblock", "block/reblock", "rights/rights",
                  "rights/autopromote", "abusefilter/modify", "abusefilter/create", "interwiki/iw_add",
                  "interwiki/iw_edit", "interwiki/iw_delete", "curseprofile/comment-created",
                  "curseprofile/comment-edited", "curseprofile/comment-deleted", "curseprofile/comment-purged",
                  "curseprofile/profile-edited", "curseprofile/comment-replied", "contentmodel/change", "sprite/sprite",
                  "sprite/sheet", "sprite/slice", "managetags/create", "managetags/delete", "managetags/activate",
                  "managetags/deactivate", "tag/update", "cargo/createtable", "cargo/deletetable",
                  "cargo/recreatetable", "cargo/replacetable", "upload/revert", "newusers/create",
                  "newusers/autocreate", "newusers/create2", "newusers/byemail", "newusers/newusers",
                  "managewiki/settings", "managewiki/delete", "managewiki/lock", "managewiki/unlock",
                  "managewiki/namespaces", "managewiki/namespaces-delete", "managewiki/rights", "managewiki/undelete"}

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
		self.map_ips = {}
		self.downtimecredibility = 0
		self.last_downtime = 0
		self.tags = {}
		self.groups = {}
		self.streak = -1
		self.mw_messages = {}
		self.namespaces = None
		self.session = session
		self.logged_in = False
		self.initial_run_complete = False

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

	def fetch(self, amount=settings["limit"]):
		messagequeue.resend_msgs()
		last_check = self.fetch_changes(amount=amount)
		if last_check is not None:
			storage["rcid"] = last_check[0] if last_check[0] else storage["rcid"]
			storage["abuse_log_id"] = last_check[1] if last_check[1] else storage["abuse_log_id"]
			storage.save_datafile()
		self.initial_run_complete = True

	def fetch_recentchanges_request(self, amount):
		"""Make a typical MW request for rc/abuselog

		If succeeds return the .json() of request and if not raises ConnectionError"""
		request = self.safe_request(WIKI_API_PATH, params=self.construct_params(amount))
		if request is not None:
			try:
				request = request.json()
			except ValueError:
				logger.warning("ValueError in fetching changes")
				logger.warning("Changes URL:" + request.url)
				self.downtime_controller(True)
				raise ConnectionError
			return request
		raise ConnectionError

	def construct_params(self, amount):
		"""Constructs GET parameters for recentchanges/abuselog fetching feature"""
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

	def prepare_rc(self, changes: list, amount: int):
		"""Processes recent changes messages"""
		if not changes:
			return None
		categorize_events = {}
		new_events = 0
		changes.reverse()
		recent_id = storage["rcid"]
		dry_run = True if recent_id is None else False
		for change in changes:
			if not dry_run and not (change["rcid"] <= recent_id):
				new_events += 1
				logger.debug(
					"New event: {}".format(change["rcid"]))
				if new_events == settings["limit"] and not (amount == settings["limitrefetch"] and self.initial_run_complete is False):
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
						if recent_changes.mw_messages["recentchanges-page-added-to-category"] in comment_to_match or \
								recent_changes.mw_messages[
									"recentchanges-page-added-to-category-bundled"] in comment_to_match:
							categorize_events[change["revid"]]["new"].add(cat_title)
							logger.debug("Matched {} to added category for {}".format(cat_title, change["revid"]))
						elif recent_changes.mw_messages[
							"recentchanges-page-removed-from-category"] in comment_to_match or \
								recent_changes.mw_messages[
									"recentchanges-page-removed-from-category-bundled"] in comment_to_match:
							categorize_events[change["revid"]]["removed"].add(cat_title)
							logger.debug("Matched {} to removed category for {}".format(cat_title, change["revid"]))
						else:
							logger.debug(
								"Unknown match for category change with messages {}, {}, {}, {} and comment_to_match {}".format(
									recent_changes.mw_messages["recentchanges-page-added-to-category"],
									recent_changes.mw_messages["recentchanges-page-removed-from-category"],
									recent_changes.mw_messages["recentchanges-page-removed-from-category-bundled"],
									recent_changes.mw_messages["recentchanges-page-added-to-category-bundled"],
									comment_to_match))
					else:
						logger.warning(
							"Init information not available, could not read category information. Please restart the bot.")
				else:
					logger.debug("Log entry got suppressed, ignoring entry.")
		if not dry_run:
			for change in changes:
				if change["rcid"] <= recent_id:
					logger.debug("Change ({}) is lower or equal to recent_id {}".format(change["rcid"], recent_id))
					continue
				logger.debug(recent_id)
				essential_info(change, categorize_events.get(change.get("revid"), None))
		return change["rcid"]

	def prepare_abuse_log(self, abuse_log: list):
		if not abuse_log:
			return None
		abuse_log.reverse()
		recent_id = storage["abuse_log_id"]
		dryrun = True if recent_id is None else False
		for entry in abuse_log:
			if dryrun:
				continue
			if entry["id"] <= recent_id:
				continue
			abuselog_processing(entry, self)
		return entry["id"]

	def fetch_changes(self, amount):
		"""Fetches the :amount: of changes from the wiki.
		Returns None on error and int of rcid of latest change if succeeded"""
		global logged_in
		rc_last_id = None
		abuselog_last_id = None
		try:
			request_json = self.fetch_recentchanges_request(amount)
		except ConnectionError:
			return
		try:
			rc = request_json["query"]['recentchanges']
		except KeyError:
			logger.warning("Path query.recentchanges not found inside request body. Skipping...")
			return
		else:
			rc_last_id = self.prepare_rc(rc, amount)
		if settings.get("show_abuselog", False):
			try:
				abuselog = request_json["query"]["abuselog"]  # While LYBL approach would be more performant when abuselog is not in request body, I prefer this approach for its clarity
			except KeyError:
				if "warnings" in request_json:
					warnings = request_json.get("warnings", {"query": {"*": ""}})
					if "Unrecognized value for parameter \"list\": abuselog." in warnings["query"]["*"]:
						settings["show_abuselog"] = False
						logger.warning("AbuseLog extension is not enabled on the wiki. Disabling the function...")
			else:
				abuselog_last_id = self.prepare_abuse_log(abuselog)
		return rc_last_id, abuselog_last_id

	def safe_request(self, url, params=None):
		try:
			if params:
				request = self.session.get(url, params=params, timeout=10, allow_redirects=False)
			else:
				request = self.session.get(url, timeout=10, allow_redirects=False)
		except requests.exceptions.Timeout:
			logger.warning("Reached timeout error for request on link {url}".format(url=url))
			self.downtime_controller(True)
			return None
		except requests.exceptions.ConnectionError:
			logger.warning("Reached connection error for request on link {url}".format(url=url))
			self.downtime_controller(True)
			return None
		except requests.exceptions.ChunkedEncodingError:
			logger.warning("Detected faulty response from the web server for request on link {url}".format(url=url))
			self.downtime_controller(True)
			return None
		else:
			if 499 < request.status_code < 600:
				self.downtime_controller(True)
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

	def downtime_controller(self, down):
		if not settings["show_updown_messages"]:
			return
		if down:
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
		else:
			if self.downtimecredibility > 0:
				self.downtimecredibility -= 1
				if self.streak > -1:
					self.streak += 1
				if self.streak > 8:
					self.streak = -1
					send_simple("down_detector", _("Connection to {wiki} seems to be stable now.").format(
						wiki=settings["wikiname"]),
					            _("Connection status"), settings["avatars"]["connection_restored"])

	def clear_cache(self):
		self.map_ips = {}
		if AUTO_SUPPRESSION_ENABLED:
			from src.fileio.database import clean_entries
			clean_entries()

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
	if "userhidden" in change:
		change["user"] = _("hidden")
	if change.get("ns", -1) in settings.get("ignored_namespaces", ()):
		return
	if change["type"] in ["edit", "new"]:
		logger.debug("List of categories in essential_info: {}".format(changed_categories))
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