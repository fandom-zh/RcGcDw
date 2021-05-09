# This file is part of Recent changes Goat compatible Discord webhook (RcGcDw).

# RcGcDw is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# RcGcDw is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with RcGcDw.  If not, see <http://www.gnu.org/licenses/>.




def compact_formatter(post_type, post, article_paths):
	"""Compact formatter for Fandom discussions."""
	message = None

	if post_type == "FORUM":


	event_type = "discussion"
	if post_type == "FORUM":

	elif post_type == "WALL":

	elif post_type == "ARTICLE_COMMENT":

	else:
		discussion_logger.warning("No entry for {event} with params: {params}".format(event=post_type, params=post))
		if not settings["support"]:
			return
		else:
			message = _("Unknown event `{event}` by [{author}]({author_url}), report it on the [support server](<{support}>).").format(
				event=post_type, author=author, author_url=author_url, support=settings["support"])
			event_type = "unknown"
	send_to_discord(DiscordMessage("compact", event_type, settings["fandom_discussions"]["webhookURL"], content=message), meta=DiscordMessageMetadata("POST"))


def embed_formatter(post_type, post, article_paths):
	"""Embed formatter for Fandom discussions."""
	if post_type == "FORUM":
		pass
	el
	if post_type == "FORUM":

	elif post_type == "WALL":

	elif post_type == "ARTICLE_COMMENT":

	else:
		discussion_logger.warning("No entry for {event} with params: {params}".format(event=post_type, params=post))
		embed["title"] = _("Unknown event `{event}`").format(event=post_type)
		embed.event_type = "unknown"
		if settings.get("support", None):
			change_params = "[```json\n{params}\n```]({support})".format(params=json.dumps(post, indent=2),
			                                                             support=settings["support"])
			if len(change_params) > 1000:
				embed.add_field(_("Report this on the support server"), settings["support"])
			else:
				embed.add_field(_("Report this on the support server"), change_params)
	embed.finish_embed()
	send_to_discord(embed, meta=DiscordMessageMetadata("POST"))


