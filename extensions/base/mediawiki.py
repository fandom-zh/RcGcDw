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
from src.api.util import embed_helper
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
	embed["link"] = "{wiki}index.php?title={article}&curid={pageid}&diff={diff}&oldid={oldrev}".format(
		wiki=ctx.client.WIKI_SCRIPT_PATH, pageid=change["pageid"], diff=change["revid"], oldrev=change["old_revid"],
		article=change["title"].replace(" ", "_").replace("%", "%25").replace("\\", "%5C").replace("&", "%26"))
	embed["title"] = "{redirect}{article} ({new}{minor}{bot}{space}{editsize})".format(
		redirect="⤷ " if "redirect" in change else "", article=change["title"], editsize="+" + str(
			editsize) if editsize > 0 else editsize, new=_("(N!) ") if action == "new" else "",
		minor=_("m") if action == "edit" and "minor" in change else "", bot=_('b') if "bot" in change else "",
		space=" " if "bot" in change or (action == "edit" and "minor" in change) or action == "new" else "")
	if settings["appearance"]["embed"]["show_edit_changes"]:
		try:
			if action == "new":
				changed_content = ctx.client.make_api_request(
					"?action=compare&format=json&torev={diff}&topst=1&prop=diff".format(diff=change["revid"]
					), "compare", "*")
			else:
				changed_content = ctx.client.make_api_request(
					"?action=compare&format=json&fromrev={oldrev}&torev={diff}&topst=1&prop=diff".format(
						diff=change["revid"], oldrev=change["old_revid"]), "compare", "*")
		except ServerError:
			changed_content = None
		if changed_content:
			EditDiff = ctx.client.content_parser()
			EditDiff.feed(changed_content)
			if EditDiff.small_prev_del:
				if EditDiff.small_prev_del.replace("~~", "").isspace():
					EditDiff.small_prev_del = _('__Only whitespace__')
				else:
					EditDiff.small_prev_del = EditDiff.small_prev_del.replace("~~~~", "")
			if EditDiff.small_prev_ins:
				if EditDiff.small_prev_ins.replace("**", "").isspace():
					EditDiff.small_prev_ins = _('__Only whitespace__')
				else:
					EditDiff.small_prev_ins = EditDiff.small_prev_ins.replace("****", "")
			logger.debug("Changed content: {}".format(EditDiff.small_prev_ins))
			if EditDiff.small_prev_del and not action == "new":
				embed.add_field(_("Removed"), "{data}".format(data=EditDiff.small_prev_del), inline=True)
			if EditDiff.small_prev_ins:
				embed.add_field(_("Added"), "{data}".format(data=EditDiff.small_prev_ins), inline=True)
		else:
			logger.warning("Unable to download data on the edit content!")
	return embed


@formatter.compact(event="edit", mode="compact")
def compact_edit(ctx: Context, change: dict):
	action = ctx.event
	edit_link = link_formatter("{wiki}index.php?title={article}&curid={pageid}&diff={diff}&oldid={oldrev}".format(
		wiki=ctx.client.WIKI_SCRIPT_PATH, pageid=change["pageid"], diff=change["revid"], oldrev=change["old_revid"],
		article=change["title"]))
	logger.debug(edit_link)
	edit_size = change["newlen"] - change["oldlen"]
	sign = ""
	if edit_size > 0:
		sign = "+"
	bold = ""
	if abs(edit_size) > 500:
		bold = "**"
	if change["title"].startswith("MediaWiki:Tag-"):
		pass
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


# Page creation - event new

@formatter.embed(event="new", mode="embed")
def embed_new(ctx, change):
	return embed_edit(ctx, change)


@formatter.compact(event="new", mode="compact")
def compact_new(ctx, change):
	return compact_edit(ctx, change)

