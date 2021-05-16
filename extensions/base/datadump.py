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
from src.api.util import embed_helper, compact_author, create_article_path, sanitize_to_markdown, sanitize_to_url, compact_summary

_ = formatters_i18n.gettext
ngettext = formatters_i18n.ngettext


# DataDumps - https://www.mediawiki.org/wiki/Extension:DataDump
# datadump/generate - Generating a dump of wiki


@formatter.embed(event="datadump/generate")
def embed_datadump_generate(ctx: Context, change: dict) -> DiscordMessage:
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change)
    embed["title"] = _("Generated {file} dump").format(file=change["logparams"]["filename"])
    embed["url"] = create_article_path(sanitize_to_url(change["title"]))
    return embed


@formatter.compact(event="mdatadump/generate")
def compact_datadump_generate(ctx: Context, change: dict):
    author, author_url = compact_author(ctx, change)
    parsed_comment = compact_summary(ctx)
    content = _("[{author}]({author_url}) generated *{file}* dump{comment}").format(
        author=author, author_url=author_url, file=sanitize_to_markdown(change["logparams"]["filename"]),
        comment=parsed_comment
    )
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)

# datadump/delete - Deleting a dump of a wiki


@formatter.embed(event="datadump/delete")
def embed_datadump_delete(ctx: Context, change: dict) -> DiscordMessage:
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change)
    embed["title"] = _("Deleted {file} dump").format(file=sanitize_to_markdown(change["logparams"]["filename"]))
    embed["url"] = create_article_path(sanitize_to_url(change["title"]))
    return embed


@formatter.compact(event="mdatadump/delete")
def compact_datadump_delete(ctx: Context, change: dict) -> DiscordMessage:
    author, author_url = compact_author(ctx, change)
    parsed_comment = compact_summary(ctx)
    content = _("[{author}]({author_url}) deleted *{file}* dump{comment}").format(
        author=author, author_url=author_url, file=sanitize_to_markdown(change["logparams"]["filename"]),
        comment=parsed_comment
    )
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)
