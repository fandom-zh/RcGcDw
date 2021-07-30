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
from src.discord.message import DiscordMessage
from src.api import formatter
from src.i18n import formatters_i18n
from src.api.context import Context
from src.api.util import embed_helper, compact_summary, clean_link, compact_author, create_article_path, sanitize_to_markdown, sanitize_to_url

_ = formatters_i18n.gettext
ngettext = formatters_i18n.ngettext


# Renameuser - https://www.mediawiki.org/wiki/Extension:Renameuser
# renameuser/renameuser - Renaming a user


@formatter.embed(event="renameuser/renameuser")
def embed_renameuser_renameuser(ctx: Context, change: dict) -> DiscordMessage:
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change)
    edits = change["logparams"]["edits"]
    if edits > 0:
        embed["title"] = ngettext("Renamed user \"{old_name}\" with {edits} edit to \"{new_name}\"",
                                  "Renamed user \"{old_name}\" with {edits} edits to \"{new_name}\"", edits).format(
            old_name=sanitize_to_markdown(change["logparams"]["olduser"]), edits=edits,
            new_name=sanitize_to_markdown(change["logparams"]["newuser"]))
    else:
        embed["title"] = _("Renamed user \"{old_name}\" to \"{new_name}\"").format(
            old_name=sanitize_to_markdown(change["logparams"]["olduser"]),
            new_name=sanitize_to_markdown(change["logparams"]["newuser"]))
    embed["url"] = create_article_path("User:" + sanitize_to_url(change["logparams"]["newuser"]))
    return embed


@formatter.compact(event="renameuser/renameuser")
def compact_renameuser_renameuser(ctx: Context, change: dict) -> DiscordMessage:
    author, author_url = compact_author(ctx, change)
    link = clean_link(create_article_path("User:" + sanitize_to_url(change["logparams"]["newuser"])))
    edits = change["logparams"]["edits"]
    parsed_comment = compact_summary(ctx)
    if edits > 0:
        content = ngettext(
            "[{author}]({author_url}) renamed user *{old_name}* with {edits} edit to [{new_name}]({link}){comment}",
            "[{author}]({author_url}) renamed user *{old_name}* with {edits} edits to [{new_name}]({link}){comment}",
            edits).format(
            author=author, author_url=author_url, old_name=sanitize_to_markdown(change["logparams"]["olduser"]),
            edits=edits,
            new_name=sanitize_to_markdown(change["logparams"]["newuser"]), link=link, comment=parsed_comment
        )
    else:
        content = _("[{author}]({author_url}) renamed user *{old_name}* to [{new_name}]({link}){comment}").format(
            author=author, author_url=author_url, old_name=sanitize_to_markdown(change["logparams"]["olduser"]),
            new_name=sanitize_to_markdown(change["logparams"]["newuser"]), link=link, comment=parsed_comment
        )
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)
