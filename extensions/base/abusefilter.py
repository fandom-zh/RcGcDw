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

import ipaddress
import logging
from src.discord.message import DiscordMessage
from src.api import formatter
from src.i18n import rc_formatters
from src.api.context import Context
from src.api.util import embed_helper, sanitize_to_url, parse_mediawiki_changes, clean_link, compact_author, \
	create_article_path, sanitize_to_markdown
from src.configloader import settings

_ = rc_formatters.gettext
ngettext = rc_formatters.ngettext

abusefilter_results = {"": _("None"), "warn": _("Warning issued"), "block": _("**Blocked user**"), "tag": _("Tagged the edit"), "disallow": _("Disallowed the action"), "rangeblock": _("**IP range blocked**"), "throttle": _("Throttled actions"), "blockautopromote": _("Removed autoconfirmed group"), "degroup": _("**Removed from privileged groups**")}
abusefilter_actions = {"edit": _("Edit"), "upload": _("Upload"), "move": _("Move"), "stashupload": _("Stash upload"), "delete": _("Deletion"), "createaccount": _("Account creation"), "autocreateaccount": _("Auto account creation")}

logger = logging.getLogger("extensions.base")


def abuse_filter_format_user(change):
	author = change["user"]
	if settings.get("hide_ips", False):
		try:
			ipaddress.ip_address(change["user"])
		except ValueError:
			pass
		else:
			author = _("Unregistered user")
	return author


@formatter.embed(event="abuselog")
def embed_abuselog(ctx, change):
	action = "abuselog/{}".format(change["result"])
	embed = DiscordMessage("embed", action, settings["webhookURL"])
	author = abuse_filter_format_user(change)
	embed["title"] = _("{user} triggered \"{abuse_filter}\"").format(user=author, abuse_filter=sanitize_to_markdown(change["filter"]))
	embed.add_field(_("Performed"), abusefilter_actions.get(change["action"], _("Unknown")))
	embed.add_field(_("Action taken"), abusefilter_results.get(change["result"], _("Unknown")))
	embed.add_field(_("Title"), sanitize_to_markdown(change.get("title", _("Unknown"))))
	return embed
