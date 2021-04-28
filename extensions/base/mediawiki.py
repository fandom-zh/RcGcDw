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
from src.discord.message import DiscordMessage
from src.api import formatter
from src.i18n import rc_formatters
from src.api.context import Context
from src.api.util import embed_helper, sanitize_to_url, parse_mediawiki_changes, clean_link, compact_author
from src.configloader import settings
from src.exceptions import *

_ = rc_formatters.gettext

logger = logging.getLogger("extensions.base")


# Page edit - event edit

@formatter.embed(event="edit", mode="embed")
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


@formatter.compact(event="edit", mode="compact")
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


# Page creation - event new aliases to embed_edit since they share a lot of their code

@formatter.embed(event="new", mode="embed")
def embed_new(ctx, change):
	return embed_edit(ctx, change)


@formatter.compact(event="new", mode="compact")
def compact_new(ctx, change):
	return compact_edit(ctx, change)

