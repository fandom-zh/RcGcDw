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
from src.api.client import Client, client
from src.configloader import settings


_ = rc_formatters.gettext

logger = logging.getLogger("extensions.base")


class base():
	def __init__(self, api):
		super().__init__(api)

	@formatter.embed(event="edit", mode="embed")
	def embed_edit(self, ctx: Client, change: dict) -> DiscordMessage:
		embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
		action = ctx.event
		editsize = change["newlen"] - change["oldlen"]
		if editsize > 0:
			if editsize > 6032:
				embed["color"] = 65280
			else:
				embed["color"] = 35840 + (math.floor(editsize / 52)) * 256
		elif editsize < 0:
			if editsize < -6032:
				embed["color"] = 16711680
			else:
				embed["color"] = 9175040 + (math.floor((editsize * -1) / 52)) * 65536
		elif editsize == 0:
			embed["color"] = 8750469
		if change["title"].startswith("MediaWiki:Tag-"):  # Refresh tag list when tag display name is edited
			ctx.client.refresh_internal_data()
		link = "{wiki}index.php?title={article}&curid={pageid}&diff={diff}&oldid={oldrev}".format(
			wiki=ctx.client.WIKI_SCRIPT_PATH, pageid=change["pageid"], diff=change["revid"], oldrev=change["old_revid"],
			article=change["title"].replace(" ", "_").replace("%", "%25").replace("\\", "%5C").replace("&", "%26"))
		embed["title"] = "{redirect}{article} ({new}{minor}{bot}{space}{editsize})".format(
			redirect="⤷ " if "redirect" in change else "", article=change["title"], editsize="+" + str(
				editsize) if editsize > 0 else editsize, new=_("(N!) ") if action == "new" else "",
			minor=_("m") if action == "edit" and "minor" in change else "", bot=_('b') if "bot" in change else "",
			space=" " if "bot" in change or (action == "edit" and "minor" in change) or action == "new" else "")
		if settings["appearance"]["embed"]["show_edit_changes"]:
			if action == "new":
				changed_content = safe_read(recent_changes._safe_request(
					"{wiki}?action=compare&format=json&fromtext=&torev={diff}&topst=1&prop=diff".format(
						wiki=ctx.client.WIKI_API_PATH, diff=change["revid"]
					)), "compare", "*")
			else:
				changed_content = safe_read(recent_changes._safe_request(
					"{wiki}?action=compare&format=json&fromrev={oldrev}&torev={diff}&topst=1&prop=diff".format(
						wiki=ctx.client.WIKI_API_PATH, diff=change["revid"], oldrev=change["old_revid"]
					)), "compare", "*")
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

	@formatter.compact(event="edit", mode="embed")
	def compact_edit(self, change: dict):
		return DiscordMessage()
