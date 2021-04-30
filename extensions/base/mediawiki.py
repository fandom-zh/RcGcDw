#  This file is part of Recent changes Goat compatible Discord webhook (RcGcDw).
#
#  RcGcDw is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  RcGcDw is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with RcGcDw.  If not, see <http://www.gnu.org/licenses/>.

import logging
import math
import re
import time
from src.discord.message import DiscordMessage
from src.api import formatter
from src.i18n import rc_formatters
from src.api.context import Context
from src.api.util import embed_helper, sanitize_to_url, parse_mediawiki_changes, clean_link, compact_author, create_article_path
from src.configloader import settings
from src.exceptions import *

_ = rc_formatters.gettext

logger = logging.getLogger("extensions.base")


# Page edit - event edit, New - page creation

@formatter.embed(event="edit", mode="embed", aliases=["new"])
def embed_edit(ctx: Context, change: dict) -> DiscordMessage:
	embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
	embed_helper(ctx, embed, change)
	action = ctx.event
	editsize = change["newlen"] - change["oldlen"]
	if editsize > 0:
		embed["color"] = min(65280, 35840 + (math.floor(editsize / 52)) * 256)  # Choose shade of green
	elif editsize < 0:
		embed["color"] = min(16711680, 9175040 + (math.floor(abs(editsize) / 52)) * 65536)  # Choose shade of red
	elif editsize == 0:
		embed["color"] = 8750469
	if change["title"].startswith("MediaWiki:Tag-"):  # Refresh tag list when tag display name is edited
		ctx.client.refresh_internal_data()
	# Sparse is better than dense.
	# Readability counts.
	embed["url"] = "{wiki}index.php?title={article}&curid={pageid}&diff={diff}&oldid={oldrev}".format(
		wiki=ctx.client.WIKI_SCRIPT_PATH,
		pageid=change["pageid"],
		diff=change["revid"],
		oldrev=change["old_revid"],
		article=sanitize_to_url(change["title"])
	)
	embed["title"] = "{redirect}{article} ({new}{minor}{bot}{space}{editsize})".format(
		redirect="⤷ " if "redirect" in change else "",
		article=change["title"],
		editsize="+" + str(editsize) if editsize > 0 else editsize,
		new=_("(N!) ") if action == "new" else "",
		minor=_("m") if action == "edit" and "minor" in change else "",
		bot=_('b') if "bot" in change else "",
		space=" " if "bot" in change or (action == "edit" and "minor" in change) or action == "new" else "")
	if settings["appearance"]["embed"]["show_edit_changes"]:
		try:
			if action == "new":
				changed_content = ctx.client.make_api_request(
					"?action=compare&format=json&fromslots=main&torev={diff}&fromtext-main=&topst=1&prop=diff".format(
						diff=change["revid"]), "compare", "*")
			else:
				changed_content = ctx.client.make_api_request(
					"?action=compare&format=json&fromrev={oldrev}&torev={diff}&topst=1&prop=diff".format(
						diff=change["revid"], oldrev=change["old_revid"]), "compare", "*")
		except ServerError:
			changed_content = None
		if changed_content:
			parse_mediawiki_changes(ctx, changed_content, embed)
		else:
			logger.warning("Unable to download data on the edit content!")
	embed["description"] = ctx.parsedcomment
	return embed


@formatter.compact(event="edit", mode="compact", aliases=["new"])
def compact_edit(ctx: Context, change: dict):
	parsed_comment = "" if ctx.parsedcomment is None else " *(" + ctx.parsedcomment + ")*"
	author, author_url = compact_author(ctx, change)
	action = ctx.event
	edit_link = clean_link("{wiki}index.php?title={article}&curid={pageid}&diff={diff}&oldid={oldrev}".format(
		wiki=ctx.client.WIKI_SCRIPT_PATH, pageid=change["pageid"], diff=change["revid"], oldrev=change["old_revid"],
		article=sanitize_to_url(change["title"])))
	logger.debug(edit_link)
	edit_size = change["newlen"] - change["oldlen"]
	sign = ""
	if edit_size > 0:
		sign = "+"
	bold = ""
	if abs(edit_size) > 500:
		bold = "**"
	if action == "edit":
		content = _(
			"[{author}]({author_url}) edited [{article}]({edit_link}){comment} {bold}({sign}{edit_size}){bold}").format(
			author=author, author_url=author_url, article=change["title"], edit_link=edit_link, comment=parsed_comment,
			edit_size=edit_size, sign=sign, bold=bold)
	else:
		content = _(
			"[{author}]({author_url}) created [{article}]({edit_link}){comment} {bold}({sign}{edit_size}){bold}").format(
			author=author, author_url=author_url, article=change["title"], edit_link=edit_link, comment=parsed_comment,
			edit_size=edit_size, sign=sign, bold=bold)
	return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)


# Upload - upload/reupload, upload/upload
@formatter.embed(event="upload/upload", mode="embed", aliases=["upload/overwrite", "upload/revert"])
def embed_upload_upload(ctx, change):
	license = None
	embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
	action = ctx.event
	embed_helper(ctx, embed, change)
	urls = ctx.client.make_api_request("{wiki}?action=query&format=json&prop=imageinfo&list=&meta=&titles={filename}&iiprop=timestamp%7Curl%7Carchivename&iilimit=5".format(
			wiki=ctx.WIKI_API_PATH, filename=sanitize_to_url(change["title"])), "query", "pages")
	link = create_article_path(sanitize_to_url(change["title"]))
	image_direct_url = None
	# Make a request for file revisions so we can get direct URL to the image for embed
	if urls is not None:
		logger.debug(urls)
		if "-1" not in urls:  # image still exists and not removed
			try:
				img_info = next(iter(urls.values()))["imageinfo"]
				for num, revision in enumerate(img_info):
					if revision["timestamp"] == change["logparams"]["img_timestamp"]:  # find the correct revision corresponding for this log entry
						image_direct_url = "{rev}?{cache}".format(rev=revision["url"], cache=int(time.time() * 5))  # cachebusting
						break
			except KeyError:
				logger.exception(
					"Wiki did not respond with extended information about file. The preview will not be shown.")
	else:
		logger.warning("Request for additional image information have failed. The preview will not be shown.")
	if action in ("upload/overwrite", "upload/revert"):
		if image_direct_url:
			try:
				revision = img_info[num + 1]
			except IndexError:
				logger.exception(
					"Could not analize the information about the image (does it have only one version when expected more in overwrite?) which resulted in no Options field: {}".format(
						img_info))
			else:
				undolink = "{wiki}index.php?title={filename}&action=revert&oldimage={archiveid}".format(
					wiki=ctx.client.WIKI_SCRIPT_PATH, filename=sanitize_to_url(change["title"]), archiveid=revision["archivename"])
				embed.add_field(_("Options"), _("([preview]({link}) | [undo]({undolink}))").format(
					link=image_direct_url, undolink=undolink))
			if settings["appearance"]["embed"]["embed_images"]:
				embed["image"]["url"] = image_direct_url
		if action == "upload/overwrite":
			embed["title"] = _("Uploaded a new version of {name}").format(name=change["title"])
		elif action == "upload/revert":
			embed["title"] = _("Reverted a version of {name}").format(name=change["title"])
	else:
		embed["title"] = _("Uploaded {name}").format(name=change["title"])
		if settings["license_detection"]:
			article_content = ctx.client.make_api_request(
				"{wiki}?action=query&format=json&prop=revisions&titles={article}&rvprop=content".format(
					wiki=ctx.client.WIKI_API_PATH, article=sanitize_to_url(change["title"])), "query", "pages")
			if article_content is None:
				logger.warning("Something went wrong when getting license for the image")
				return 0
			if "-1" not in article_content:
				content = list(article_content.values())[0]['revisions'][0]['*']
				try:
					matches = re.search(re.compile(settings["license_regex"], re.IGNORECASE), content)
					if matches is not None:
						license = matches.group("license")
					else:
						if re.search(re.compile(settings["license_regex_detect"], re.IGNORECASE), content) is None:
							license = _("**No license!**")
						else:
							license = "?"
				except IndexError:
					logger.error(
						"Given regex for the license detection is incorrect. It does not have a capturing group called \"license\" specified. Please fix license_regex value in the config!")
					license = "?"
				except re.error:
					logger.error(
						"Given regex for the license detection is incorrect. Please fix license_regex or license_regex_detect values in the config!")
					license = "?"
		if license is not None:
			ctx.parsedcomment += _("\nLicense: {}").format(license)
		if image_direct_url:
			embed.add_field(_("Options"), _("([preview]({link}))").format(link=image_direct_url))
			if settings["appearance"]["embed"]["embed_images"]:
				embed["image"]["url"] = image_direct_url
	return embed


@formatter.compact(event="upload/upload", mode="compact")
def compact_upload_upload(ctx, change):
	author, author_url = compact_author(ctx, change)
	file_link = clean_link(create_article_path(sanitize_to_url(change["title"])))
	content = _("[{author}]({author_url}) uploaded [{file}]({file_link}){comment}").format(author=author,
	                                                                                       author_url=author_url,
	                                                                                       file=change["title"],
	                                                                                       file_link=file_link,
	                                                                                       comment="" if ctx.parsedcomment is None else " *(" + ctx.parsedcomment + ")*")
	return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)

# delete - Page deletion
@formatter.embed(event="delete/delete", mode="embed")
def embed_delete(ctx, change):
	embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
	embed_helper(ctx, embed, change)
	link = create_article_path(sanitize_to_url(change["title"]))
	embed["title"] = _("Deleted page {article}").format(article=change["title"])
	if AUTO_SUPPRESSION_ENABLED:
		delete_messages(dict(pageid=change.get("pageid")))