#!/usr/bin/python
# -*- coding: utf-8 -*-

import time, logging, json, requests, datetime, re, gettext, math, random
from bs4 import BeautifulSoup
from collections import defaultdict
logging.basicConfig(level=logging.DEBUG)
#logging.warning('Watch out!')
#DEBUG, INFO, WARNING, ERROR, CRITICAL
pl = gettext.translation('rcgcdw', localedir='locale', languages=['pl'])
pl.install()
_ = lambda s: s

with open("settings.json") as sfile:
	settings = json.load(sfile)
logging.info("Current settings: {settings}".format(settings=settings))

def send(message, name, avatar):
	req = requests.post(settings["webhookURL"], data={"content": message, "avatar_url": avatar, "username": name}, timeout=10)
	
def safe_read(request, *keys):
	if request is None:
		return None
	try:
		request = request.json()
		for item in keys:
			request = request[item]
	except KeyError:
		logging.warning("Failure while extracting data from request on key {key} in {change}".format(key=item, change=request))
		return None
	except ValueError:
		logging.warning("Failure while extracting data from request in {change}".format(key=item, change=request))
		return None
	return request
	
def webhook_formatter(action, timestamp, **params):
	colornumber = None
	data = {}
	data["embeds"] = []
	embed = defaultdict(dict)
	if "title" in params:
		article_encoded = params["title"].replace(" ", "_").replace(')', '\)')
	if re.match(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", params["user"]) is not None:
		author_url = "https://{wiki}.gamepedia.com/Special:Contributions/{user}".format(wiki=settings["wiki"], user=params["user"])
		if params["user"] not in list(recent_changes.map_ips.keys()):
			contibs = safe_read(recent_changes.safe_request("https://{wiki}.gamepedia.com/api.php?action=query&format=json&list=usercontribs&uclimit=max&ucuser={user}&ucprop=".format(wiki=settings["wiki"], user=params["user"])), "query", "usercontribs")
			if contibs is None:
				logging.warning("WARNING: Something went wrong when checking amount of contributions for given IP address")
				params["user"] = params["user"] + "(?)"
			else:
				params["user"] = "{author} ({contribs})".format(author=params["user"], contribs=len(contibs))
				recent_changes.map_ips[params["user"]]=len(contibs)
		else:
			recent_changes.map_ips[params["user"]]+=1
			params["user"] = "{author} ({amount})".format(author=params["user"], amount=recent_changes.map_ips[params["user"]])
	else:
		author_url = "https://{wiki}.gamepedia.com/User:{user}".format(wiki=settings["wiki"], user=params["user"].replace(" ", "_"))
	if action in [1, 37]: #edit or new page
		editsize = params["size"]
		print (editsize)
		if editsize > 0:
			if editsize > 6032:
				colornumber = 65280
			else:
				colornumber = 35840 + (math.floor(editsize/(52)))*256
		elif editsize < 0:
			if editsize < -6032:
				colornumber = 16711680
			else:
				colornumber = 9175040 + (math.floor((editsize*-1)/(52)))*65536
		elif editsize == 0:
			colornumber = 8750469
		link = "https://{wiki}.gamepedia.com/index.php?title={article}&curid={pageid}&diff={diff}&oldid={oldrev}".format(wiki=settings["wiki"], pageid=params["pageid"], diff=params["diff"], oldrev=params["oldrev"], article=article_encoded)
		if action == 1:
			embed["author"]["icon_url"] = "https://d1u5p3l4wpay3k.cloudfront.net/minecraft_pl_gamepedia/d/df/Ksi%C4%85%C5%BCka_z_pi%C3%B3rem.png?version=d2b085f15fb5713091ed06f92f81c360"
		else:
			embed["author"]["icon_url"] = "https://framapic.org/VBVcOznftNsV/4a0fbBL7wkUo.png"
		embed["title"] = "{article} ({new}{minor}{editsize})".format(article=params["title"], editsize="+"+str(editsize) if editsize>0 else editsize, new= "(N!) " if action == 37 else "", minor="m " if action == 1 and params["minor"] else "")
	elif action == 5: #sending files
		urls = safe_read(recent_changes.safe_request("https://{wiki}.gamepedia.com/api.php?action=query&format=json&prop=imageinfo&list=&meta=&titles={filename}&iiprop=timestamp%7Curl&iilimit=2".format(wiki=settings["wiki"], filename=params["title"])), "query", "pages")
		undolink = ""
		link ="https://{wiki}.gamepedia.com/{article}".format(wiki=settings["wiki"], article=article_encoded)
		if urls is not None:
			img_info = next(iter(urls.values()))["imageinfo"]
			embed["image"]["url"] = img_info[0]["url"]
		else:
			return
		if params["overwrite"]:
			colornumber = 12390624
			img_timestamp = [x for x in img_info[1]["timestamp"] if x.isdigit()]
			undolink = "https://{wiki}.gamepedia.com/index.php?title={filename}&action=revert&oldimage={timestamp}%21{filenamewon}".format(wiki=settings["wiki"], filename=article_encoded, timestamp=img_timestamp, filenamewon = article_encoded[5:])
			embed["title"] = _("New file version {name}").format(name=params["title"])
			embed["fields"] = [{"name": _("Options"), "value": _("([preview]({link}) | [undo]({undolink}))").format(link=embed["image"]["url"], undolink=undolink)}]
		else:
			embed["title"] = _("New file {name}").format(name=params["title"])
			article_content = safe_read(recent_changes.safe_request("https://{wiki}.gamepedia.com/api.php?action=query&format=json&prop=revisions&titles={article}&rvprop=content".format(wiki=settings["wiki"], article=urllib.parse.quote_plus(params["title"]))), "query", "pages") #TODO Napewno urllib?
			if article_content is None:
				logging.warning("Something went wrong when getting license for the image")
				return 0
			content = list(article_content.values())[0]['revisions'][0]['*'].lower()
			if "{{license" not in content:
				license = "**No license!**"
			else:
				matches = re.search(r"\{\{license\ (.*?)\}\}", content)
				if matches is not None:
					license = matches.group(1)
				else:
					license = "?"
			embed["fields"] = [{"name": _("Options"), "value": _("([preview]({link}))").format(link=pic_url)}]
			params["desc"] = _("{desc}\nLicense: {license}").format(desc=params["desc"], license=license)
	elif action == 6:
		link = "https://{wiki}.gamepedia.com/{article}".format(wiki=settings["wiki"], article=article_encoded)
		embed["author"]["icon_url"] = "https://framapic.org/9Rgw6Vkx1L1b/R9WrMWJ6umeX.png"
		colornumber = 1
		embed["title"] = _("Deleted {article}").format(article=params["title"])
	elif action == 7:
		link = "https://{wiki}.gamepedia.com/{article}".format(wiki=settings["wiki"], article=article_encoded)
		embed["author"]["icon_url"] = "https://framapic.org/9Rgw6Vkx1L1b/R9WrMWJ6umeX.png"
		colornumber = 1
		embed["title"] = _("Deleted redirect ({article}) to make space for moved page").format(article=params["title"])
	elif action == 14:
		link = params["targetlink"]
		embed["author"]["icon_url"] = "https://i.imgur.com/ZX02KBf.png"
		params["desc"] = "{supress}. {desc}".format(desc=params["desc"], supress=_("No redirect has been made") if params["supress"] == True else _("A redirect has been made"))
		embed["title"] = _("Moved \"{article}\" to \"{target}\"").format(article = params["title"], target=params["target"])
	elif action == 15:
		link = "https://{wiki}.gamepedia.com/{article}".format(wiki=settings["wiki"], article=article_encoded)
		embed["title"] = _("Moved {article} to redirect page ({title})").format(article=params["title"], title=params["target"])
		embed["author"]["icon_url"]= "https://i.imgur.com/ZX02KBf.png"
	elif action == 16:
		link = "https://{wiki}.gamepedia.com/{article}".format(wiki=settings["wiki"], article=article_encoded)
		embed["title"] = _("Moved protection settings from {article} to {title}").format(article=params["title"], title=params["target"])
		embed["author"]["icon_url"]= "https://i.imgur.com/ZX02KBf.png"
	elif action == 17:
		link = "https://{wiki}.gamepedia.com/{user}".format(wiki=settings["wiki"], user=params["blocked_user"].replace(" ", "_").replace(')', '\)'))
		user = params["blocked_user"].split(':')[1]
		time =_( "infinity and beyond") if params["duration"] == "infinite" else params["duration"] 
		embed["title"] = _("Blocked {blocked_user} for {time}").format(blocked_user=user, time=time)
		colornumber = 1
		embed["author"]["icon_url"] = "https://i.imgur.com/g7KgZHf.png"
	elif action == 19:
		link = "https://{wiki}.gamepedia.com/{user}".format(wiki=settings["wiki"], user=params["blocked_user"].replace(" ", "_").replace(')', '\)'))
		user = params["blocked_user"].split(':')[1]
		embed["title"] = _("Reapplied the block on {blocked_user}").format(blocked_user=user)
		colornumber = 1
		embed["author"]["icon_url"] = "https://i.imgur.com/g7KgZHf.png"
	elif action == 18:
		link = "https://{wiki}.gamepedia.com/{user}".format(wiki=settings["wiki"], user=params["blocked_user"].replace(" ", "_").replace(')', '\)'))
		user = params["blocked_user"].split(':')[1]
		embed["title"] = _("Removed the block on {blocked_user}").format(blocked_user=user)
		colornumber = 1
		embed["author"]["icon_url"] = "https://i.imgur.com/g7KgZHf.png"
	elif action == 25:
		link = "https://{wiki}.gamepedia.com/UserProfile:{target}".format(wiki=settings["wiki"], target=params["target"].replace(" ", "_").replace(')', '\)'))
		embed["title"] = _("Left a comment on {target}'s profile").format(target=params["target"])
	elif action == 29:
		link = "https://{wiki}.gamepedia.com/UserProfile:{target}".format(wiki=settings["wiki"], target=params["target"].replace(" ", "_").replace(')', '\)'))
		embed["title"] = _("Replied to a comment on {target}'s profile").format(target=params["target"])
	elif action == 26:
		link = "https://{wiki}.gamepedia.com/UserProfile:{target}".format(wiki=settings["wiki"], target=params["target"].replace(" ", "_").replace(')', '\)'))
		embed["title"] = _("Edited a comment on {target}'s profile").format(target=params["target"])
	elif action == 28:
		link = "https://{wiki}.gamepedia.com/UserProfile:{target}".format(wiki=settings["wiki"], target=params["target"].replace(" ", "_").replace(')', '\)'))
		if params["field"] == "profile-location":
			field = _("Location")
		elif params["field"] == "profile-aboutme":
			field = _("About me")
		elif params["field"] == "profile-link-google":
			field = "Google link"
		elif params["field"] == "profile-link-facebook":
			field = "Facebook link"
		elif params["field"] == "profile-link-twitter":
			field = "Twitter link"
		elif params["field"] == "profile-link-reddit":
			field = "Reddit link"
		elif params["field"] == "profile-link-twitch":
			field = "Twitch link"
		elif params["field"] == "profile-link-psn":
			field = "PSN link"
		elif params["field"] == "profile-link-vk":
			field = "VK link"
		elif params["field"] == "profile-link-xbl":
			field = "XVL link"
		elif params["field"] == "profile-link-steam":
			field = "Steam link"
		else:
			field = _("Unknown")
		embed["title"] = _("Edited {target}'s profile").format(target=params["target"])
		params["desc"] = _("{field} field changed to: {desc}").format(field=field, desc=params["desc"])
	elif action == 27:
		link = "https://{wiki}.gamepedia.com/UserProfile:{target}".format(wiki=settings["wiki"], target=params["target"].replace(" ", "_").replace(')', '\)'))
		embed["title"] = _("Removed a comment on {target}'s profile").format(target=params["target"])
	elif action == 20:
		link = "https://{wiki}.gamepedia.com/"+params["user"].replace(" ", "_").replace(')', '\)')
		embed["title"] = _("Changed {target}'s user groups").format(target=params["user"])
		if params["old_groups"].count(' ') < params["new_groups"].count(' '):
			embed["thumbnail"]["url"] = "https://i.imgur.com/WnGhF5g.gif"
		if len(params["old_groups"]) < 4:
			params["old_groups"] = _("none")
		if len(params["new_groups"]) < 4:
			params["new_groups"] = _("none")
		params["desc"] = _("Groups changed from {old_groups} to {new_groups} with reason given: {desc}").format(old_groups=params["old_groups"], new_groups=params["new_groups"], desc=params["desc"])
	elif action == 2:
		link = "https://{wiki}.gamepedia.com/{article}".format(wiki=settings["wiki"], article=article_encoded)
		embed["title"] = _("Protected the page {target}").format(target=params["title"])
		embed["author"]["icon_url"] ="https://i.imgur.com/Lfk0wuw.png"
		params["desc"] = params["settings"] + " | " + params["desc"]
	elif action == 3:
		link = "https://{wiki}.gamepedia.com/{article}".format(wiki=settings["wiki"], article=article_encoded)
		embed["title"] = _("Modified protection settings for {article}").format(article=params["title"])
		params["desc"] = params["settings"] + " | " + params["desc"]
		embed["author"]["icon_url"] ="https://i.imgur.com/Lfk0wuw.png"
	elif action == 4:
		link = "https://{wiki}.gamepedia.com/{article}".format(wiki=settings["wiki"], article=article_encoded)
		embed["title"] = _("Removed protection for {article}").format(article=params["title"])
		embed["author"]["icon_url"] ="https://i.imgur.com/Lfk0wuw.png"
	elif action == 9:
		link = "https://{wiki}.gamepedia.com/{article}".format(wiki=settings["wiki"], article=article_encoded)
		embed["title"] = _("Removed revision(s) from public view for {article}").format(article=params["title"])
	elif action == 11:
		link = "https://{wiki}.gamepedia.com/{article}".format(wiki=settings["wiki"], article=article_encoded)
		embed["title"] = _("Imported {article} with {count} revision(s)").format(article=params["title"], count=params["amount"])
	elif action == 8:
		link = "https://{wiki}.gamepedia.com/{article}".format(wiki=settings["wiki"], article=article_encoded)
		embed["title"] = _("Restored {article}").format(article=params["title"])
	elif action == 10:
		link = "https://{wiki}.gamepedia.com/Special:RecentChanges".format(wiki=settings["wiki"])
		embed["title"] = _("Removed events")
	elif action == 12:
		link = "https://{wiki}.gamepedia.com/Special:RecentChanges".format(wiki=settings["wiki"])
		embed["title"] = _("Imported interwiki")
	elif action == 21:
		link = "https://{wiki}.gamepedia.com/Special:RecentChanges".format(wiki=settings["wiki"])
		embed["title"] = _("Edited abuse filter number {number}").format(number=params["filternr"])
	elif action == 8:
		link = "https://{wiki}.gamepedia.com/{article}".format(wiki=settings["wiki"], article=article_encoded)
		embed["title"] = _("Merged revision histories for {article}").format(article=params["title"])
	elif action == 22:
		link = "https://{wiki}.gamepedia.com/Special:Interwiki".format(wiki=settings["wiki"])
		embed["title"] = _("Added interwiki entry")
		params["desc"] =_("Prefix: {prefix}, website: {website} | {desc}").format(desc=params["desc"], prefix=params["prefix"], website=params["website"])
	elif action == 23:
		link = "https://{wiki}.gamepedia.com/Special:Interwiki".format(wiki=settings["wiki"])
		embed["title"] = _("Edited interwiki entry")
		params["desc"] =_("Prefix: {prefix}, website: {website} | {desc}").format(desc=params["desc"], prefix=params["prefix"], website=params["website"])
	elif action == 24:
		link = "https://{wiki}.gamepedia.com/Special:Interwiki".format(wiki=settings["wiki"])
		embed["title"] = _("Deleted interwiki entry")
		params["desc"] =_("Prefix: {prefix} | {desc}").format(desc=params["desc"], prefix=params["prefix"])
	elif action == 30:
		link = "https://{wiki}.gamepedia.com/{article}".format(wiki=settings["wiki"], article=article_encoded)
		embed["title"] = _("Changed content model of {article}").format(article=params["title"])
		params["desc"] = _("Model changed from {old} to {new}: {reason}").format(old=params["oldmodel"], new=params["newmodel"], reason=params["desc"])
	elif action == 31:
		link = "https://{wiki}.gamepedia.com/{article}".format(wiki=settings["wiki"], article=article_encoded)
		embed["title"] = _("Edited the sprite for {article}").format(article=params["title"])
	elif action == 32:
		link = "https://{wiki}.gamepedia.com/{article}".format(wiki=settings["wiki"], article=article_encoded)
		embed["title"] = _("Created the sprite sheet for {article}").format(article=params["title"])
	elif action == 33:
		link = "https://{wiki}.gamepedia.com/{article}".format(wiki=settings["wiki"], article=article_encoded)
		embed["title"] = _("Edited the slice for {article}").format(article=params["title"])
	elif action == 34:
		link = "https://{wiki}.gamepedia.com/{article}".format(wiki=settings["wiki"], article=article_encoded)
		embed["title"] = _("Created a tag \"{tag}\"").format(article=params["additional"]["tag"])
	elif action == 35:
		link = "https://{wiki}.gamepedia.com/{article}".format(wiki=settings["wiki"], article=article_encoded)
		embed["title"] = _("Deleted a tag \"{tag}\"").format(article=params["additional"]["tag"])
	else:
		logging.warning("No entry for {event} with params: {params}".format(event=action, params=params))
	embed["author"]["name"] = params["user"]
	embed["author"]["url"] = author_url
	embed["url"] = link
	if "desc" not in params:
		params["desc"] = ""
	embed["description"] = params["desc"]
	embed["color"] = random.randrange(1, 16777215) if colornumber is None else math.floor(colornumber)
	embed["timestamp"] = timestamp
	data["embeds"].append(dict(embed))
	formatted_embed = json.dumps(data, indent=4)
	headers = {'Content-Type': 'application/json'}
	#logging.debug(data)
	result = requests.post(settings["webhookURL"], data=formatted_embed, headers=headers)
		
def first_pass(change):
	parsedcomment = (BeautifulSoup(change["parsedcomment"], "lxml")).get_text()
	if not parsedcomment:
		parsedcomment = _("No description provided")
	if change["type"] == "edit":
		webhook_formatter(1,  change["timestamp"], user=change["user"], title=change["title"], desc=parsedcomment, oldrev=change["old_revid"], pageid=change["pageid"], diff=change["revid"], size=change["newlen"]-change["oldlen"], minor= True if "minor" in change else False)
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
			webhook_formatter(14, change["timestamp"], user=change["user"], title=change["title"], desc=parsedcomment, supress=True if "suppressredirect" in change["logparams"] else False, target=change["logparams"]['target_title'], targetlink="https://{wiki}.gamepedia.com/".format(wiki=settings["wiki"]) + change["logparams"]['target_title'].replace(" ", "_")) #TODO Remove the link making in here
		elif logtype=="move" and logaction=="move_redir":
			webhook_formatter(15, change["timestamp"], user=change["user"], title=change["title"], desc=parsedcomment, target=change["logparams"]["target_title"])
		elif logtype=="protect" and logaction=="move_prot":
			webhook_formatter(16, change["timestamp"], user=change["user"], title=change["title"], desc=parsedcomment, target=change["logparams"]["oldtitle_title"])
		elif logtype=="block" and logaction=="block":
			webhook_formatter(17, change["timestamp"], user=change["user"], blocked_user=change["title"], desc=parsedcomment, duration=change["logparams"]["duration"])
		elif logtype=="block" and logaction=="unblock":
			webhook_formatter(18, change["timestamp"], user=change["user"], blocked_user=change["title"], desc=parsedcomment)
		elif logtype=="block":
			webhook_formatter(19, change["timestamp"], user=change["user"], blocked_user=change["title"], desc=parsedcomment)
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
			webhook_formatter(34, change["timestamp"], user=change["user"], title=change["title"], desc=parsedcomment, additional=change["params"])
		elif logtype=="managetags" and logaction=="delete":
			webhook_formatter(35, change["timestamp"], user=change["user"], title=change["title"], desc=parsedcomment, additional=change["params"])
		elif logtype=="tag" and logaction=="update":
			webhook_formatter(36, change["timestamp"], user=change["user"], title=change["title"], desc=parsedcomment)
		else:
			logging.warning("No entry matches given change!")
			print (change)
			send(_("Unable to process the event"), _("error"), "")
			return
		if change["type"] == "external": #not sure what happens then, but it's listed as possible type
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
	map_ips = {}
	recent_id = 0
	downtimecredibility = 0
	last_downtime = 0
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
		changes = self.safe_request("https://{wiki}.gamepedia.com/api.php?action=query&format=json&list=recentchanges&rcshow=!bot&rcprop=title%7Ctimestamp%7Cids%7Cloginfo%7Cparsedcomment%7Csizes%7Cflags%7Ctags%7Cuser&rclimit={amount}&rctype=edit%7Cnew%7Clog%7Cexternal".format(wiki=settings["wiki"], amount=settings["limit"]))
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
				for change in changes:
					if change["rcid"] in self.ids:
						continue
					self.add_cache(change)
					if clean:
						continue
					first_pass(change)
					time.sleep(0.5)
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
			if (time.time() - self.last_downtime)>1800 and self.check_connection(): #check if last downtime happened within 30 minutes, if yes, don't send a message
				send(_("{wiki} seems to be down or unreachable.").format(wiki=settings["wiki"]), _("Connection status"), _("https://i.imgur.com/2jWQEt1.png"))
				self.last_downtime = time.time()
	
recent_changes = recent_changes()
recent_changes.fetch()
	
while 1:
	time.sleep(float(settings["cooldown"]))
	recent_changes.fetch()
	if (recent_changes.day != datetime.date.fromtimestamp(time.time()).day):
		logging.info("A brand new day! Printing the summary and clearing the cache")
		#recent_changes.summary()
		#recent_changes.clear_cache()
