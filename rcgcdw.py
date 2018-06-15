#!/usr/bin/python
# -*- coding: utf-8 -*-

import time, logging, json, requests, datetime
from bs4 import BeautifulSoup
logging.basicConfig(level=logging.DEBUG)
#logging.warning('Watch out!')
#DEBUG, INFO, WARNING, ERROR, CRITICAL

with open("settings.json") as sfile:
	settings = json.load(sfile)
logging.info("Current settings: {settings}".format(settings=settings))

def send(message, name, avatar):
	req = requests.post(settings["webhookURL"], data={"content": message, "avatar_url": avatar, "username": name}, timeout=10)
	
def webhook_formatter(action, timestamp, **params):
	
	
def first_pass(change):
	parsedcomment = (BeautifulSoup(change["parsedcomment"], "lxml")).get_text()
	if not parsedcomment:
		parsedcomment = "No description provided"
	if change["type"] == "edit":
		minor = True if "minor" in change else False
		webhook_formatter(1,  change["timestamp"], user=change["user"], title=change["title"], desc=parsedcomment, old_revid=change["old_revid"], pageid=change["pageid"], revid=change["revid"], length=change["newlen"]-change["oldlen"], minor=minor)
	elif change["type"] == "log":
		logtype = change["logtype"]
		logaction = change["logaction"]
		if logtype=="protect" and logaction=="protect":
			webhook_formatter(2, change["timestamp"], user=change["user"], title=change["title"], desc=parsedcomment, settings=change["logparams"]["description"])
		elif logtype=="protect" and logaction=="modify":
			webhook_formatter(3, change["timestamp"], user=change["user"], title=change["title"], desc=parsedcomment, settings=change["logparams"]["description"])
		elif logtype=="protect" and logaction=="unprotect":
			webhook_formatter(4, change["timestamp"], user=change["user"], title=change["title"], desc=parsedcomment)
		elif logtype=="upload" and logaction=="overwrite":
			webhook_formatter(5, change["timestamp"], user=change["user"], title=change["title"], desc=parsedcomment,  overwrite=True)
		elif logtype=="upload":
			webhook_formatter(5, change["timestamp"], user=change["user"], title=change["title"], desc=parsedcomment,  overwrite=False)
		elif logtype=="delete" and logaction=="delete":
			webhook_formatter(6, change["timestamp"], user=change["user"], title=change["title"], desc=parsedcomment)
		elif logtype=="delete" and logaction=="delete_redir":
			webhook_formatter(7, change["timestamp"], user=change["user"], title=change["title"], desc=parsedcomment)
		elif logtype=="delete" and logaction=="restore":
			webhook_formatter(8, change["timestamp"], user=change["user"], title=change["title"], desc=parsedcomment)
		elif logtype=="delete" and logaction=="revision":
			webhook_formatter(9, change["timestamp"], user=change["user"], title=change["title"], desc=parsedcomment)
		elif logtype=="delete" and logaction=="event":
			webhook_formatter(10, change["timestamp"], user=change["user"], desc=parsedcomment)
		elif logtype=="import" and logaction=="upload":
			webhook_formatter(11, change["timestamp"], user=change["user"], title=change["title"], desc=parsedcomment, amount=change["logparams"]["count"])
		elif logtype=="import" and logaction=="interwiki":
			webhook_formatter(12, change["timestamp"], user=change["user"], desc=parsedcomment)
		elif logtype=="merge" :
			webhook_formatter(13, change["timestamp"], user=change["user"], title=change["title"], desc=parsedcomment)
		elif logtype=="move" and logaction=="move":
			webhook_formatter(14, change["timestamp"], user=change["user"], title=change["title"], desc=parsedcomment, supress=True if "suppressredirect" in change["logparams"] else False, target=change["logparams"]['target_title'], targetlink="https://minecraft.gamepedia.com/" + change["logparams"]['target_title'].replace(" ", "_")) #TODO Remove the link making in here
		elif logtype=="move" and logaction=="move_redir":
			webhook_formatter(15, change["timestamp"], user=change["user"], title=change["title"], desc=parsedcomment, target=change["logparams"]["target_title"])
		elif logtype=="protect" and logaction=="move_prot":
			webhook_formatter(16, change["timestamp"], user=change["user"], title=change["title"], desc=parsedcomment, target=change["logparams"]["oldtitle_title"])
		elif logtype=="block" and logaction=="block":
			webhook_formatter(17, change["timestamp"], user=change["user"], title=change["title"], desc=parsedcomment, duration=change["logparams"]["duration"])
		elif logtype=="block" and logaction=="unblock":
			webhook_formatter(18, change["timestamp"], user=change["user"], title=change["title"], desc=parsedcomment)
		elif logtype=="block":
			webhook_formatter(19, change["timestamp"], user=change["user"], title=change["title"], desc=parsedcomment)
		elif logtype=="rights":
			webhook_formatter(20, change["timestamp"], user=change["user"], title=change["title"], desc=parsedcomment, old_groups=' '.join(change["logparams"]["oldgroups"]), new_groups=' '.join(change["logparams"]["newgroups"]))
		elif logtype=="abusefilter":
			webhook_formatter(21, change["timestamp"], user=change["user"], desc=parsedcomment, filternr=change["logparams"]['1'])
		elif logtype=="interwiki" and logaction=="iw_add":
			webhook_formatter(22, change["timestamp"], user=change["user"], desc=parsedcomment, prefix=change["logparams"]['0'], website=change["logparams"]['1'])
		elif logtype=="interwiki" and logaction=="iw_edit":
			webhook_formatter(23, change["timestamp"], user=change["user"], desc=parsedcomment, prefix=change["logparams"]['0'], website=change["logparams"]['1'])
		elif logtype=="interwiki" and logaction=="iw_delete":
			webhook_formatter(24, change["timestamp"], user=change["user"], desc=parsedcomment, prefix=change["logparams"]['0'])
		elif logtype=="curseprofile" and logaction=="comment-created":
			webhook_formatter(25, change["timestamp"], user=change["user"], target=change["title"].split(':')[1])
		elif logtype=="curseprofile" and logaction=="comment-edited":
			webhook_formatter(26, change["timestamp"], user=change["user"], target=change["title"].split(':')[1])
		elif logtype=="curseprofile" and logaction=="comment-deleted":
			webhook_formatter(27, change["timestamp"], user=change["user"], target=change["title"].split(':')[1])
		elif logtype=="curseprofile" and logaction=="profile-edited":
			webhook_formatter(28, change["timestamp"], user=change["user"], target=change["title"].split(':')[1], field=change["logparams"]['0'], desc=change["parsedcomment"])
		elif logtype=="curseprofile" and logaction=="comment-replied":
			webhook_formatter(29, change["timestamp"], user=change["user"], target=change["title"].split(':')[1])
		elif logtype=="contentmodel" and logaction=="change":
			webhook_formatter(30, change["timestamp"], user=change["user"], title=change["title"], desc=parsedcomment, oldmodel=change["logparams" ]["oldmodel"], newmodel=change["logparams" ]["newmodel"])
		elif logtype=="sprite" and logaction=="sprite":
			webhook_formatter(31, change["timestamp"], user=change["user"], title=change["title"], desc=parsedcomment)
		elif logtype=="sprite" and logaction=="sheet":
			webhook_formatter(32, change["timestamp"], user=change["user"], title=change["title"], desc=parsedcomment)
		elif logtype=="sprite" and logaction=="slice":
			webhook_formatter(33, change["timestamp"], user=change["user"], title=change["title"], desc=parsedcomment)
		elif logtype=="managetags" and logaction=="create":
			webhook_formatter(34, change["timestamp"], user=change["user"], title=change["title"], desc=parsedcomment)
		elif logtype=="managetags" and logaction=="delete":
			webhook_formatter(35, change["timestamp"], user=change["user"], title=change["title"], desc=parsedcomment)
		elif logtype=="tag" and logaction=="update":
			webhook_formatter(36, change["timestamp"], user=change["user"], title=change["title"], desc=parsedcomment)
		else:
			logging.warning("No entry matches given change!")
			print (change)
			send("Unable to process the event", "error", avatar)
			return
		elif change["type"] == "external": #not sure what happens then, but it's listed as possible type
			logging.warning("External event happened, ignoring.")
			print (change)
			return
		elif change["type"] == "new": #new page
			webhook_formatter(37, change["timestamp"], user=change["user"], title=change["title"], desc=parsedcomment, oldrev=change["old_revid"], pageid=change["pageid"], diff=change["revid"], size=change["newlen"])
		

class recent_changes(object):
	starttime = time.time()
	day = datetime.date.fromtimestamp(time.time()).day
	cache = []
	ids = []
	recent_id = 0
	downtimecredibility = 0
	def add_cache(self, change):
		self.cache.append(change)
		self.ids.append(change["rcid"])
		self.recent_id = change["rcid"]
		if len(self.ids) > settings["limit"]+5:
			self.ids.pop(0)
	def fetch(self):
		self.recent_id = self.fetch_changes()
	def fetch_changes(self, clean=False):
		if len(self.cache) == 0:
			logging.debug("cache is empty, triggering clean fetch")
			clean = True
		changes = safe_request("https://{wiki}.gamepedia.com/api.php?action=query&format=json&list=recentchanges&rcshow=!bot&rcprop=title%7Ctimestamp%7Cids%7Cloginfo%7Cparsedcomment%7Csizes%7Cflags%7Ctags%7Cuser&rclimit={amount}&rctype=edit%7Cnew%7Clog%7Cexternal".format(wiki=settings["wiki"], amount=settings["limit"]))
		if changes:
			try:
				changes = changes.json()['query']['recentchanges']
				changes.reverse()
			except ValueError:
				logging.warning("ValueError in fetching changes")
				self.downtime_controller()
				return None
			except KeyError:
				logging.warning("Wiki returned %s" % (request.json()))
				return None
			else:
				for change in pchanges:
					if change["rcid"] in self.ids:
						continue
					self.add_cache(change)
					if clean:
						continue
					
	def safe_request(self, url):
		try:
			request = requests.get(url, timeout=10, headers=settings["header"])
		except requests.exceptions.Timeout:
			logging.warning("Reached timeout error for request on link {url}")
			self.downtime_controller()
			return None
		except requests.exceptions.ConnectionError:
			logging.warning("Reached connection error for request on link {url}")
			self.downtime_controller()
			return None
		else:
			return request
	def check_connection(self):
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
			logging.error("Failure when checking Internet connection at {time}".format(time=time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime())))
			return False
		return True
	def downtime_controller(self):
		if self.downtimecredibility<60:
			self.downtimecredibility+=15
		else:
			if self.check_connection():
				send(_("Minecraft Wiki seems to be down or unreachable."), _("Connection status"), _("https://i.imgur.com/2jWQEt1.png"))
	
recent_changes = recent_changes()
	
while 1:
	time.sleep(settings["cooldown"])
	if (recent_changes.day != datetime.date.fromtimestamp(time.time()).day):
		logging.info("A brand new day! Printing the summary and clearing the cache")
		recent_changes.summary()
		recent_changes.clear_cache()
