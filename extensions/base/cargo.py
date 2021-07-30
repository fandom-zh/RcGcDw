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
import re
from src.discord.message import DiscordMessage
from src.api import formatter
from src.i18n import formatters_i18n
from src.api.context import Context
from src.api.util import embed_helper, compact_author, create_article_path, sanitize_to_markdown

_ = formatters_i18n.gettext
ngettext = formatters_i18n.ngettext


# Cargo - https://www.mediawiki.org/wiki/Extension:Cargo
# cargo/createtable - Creation of Cargo table

@formatter.embed(event="cargo/createtable")
def embed_cargo_createtable(ctx: Context, change: dict):
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change)
    table = re.search(r"\[(.*?)]\(<(.*?)>\)", ctx.client.parse_links(change["logparams"]["0"]))
    embed["url"] = table.group(2)
    embed["title"] = _("Created the Cargo table \"{table}\"").format(table=table.group(1))
    return embed


@formatter.compact(event="cargo/createtable")
def compact_cargo_createtable(ctx: Context, change: dict):
    author, author_url = compact_author(ctx, change)
    table = re.search(r"\[(.*?)]\(<(.*?)>\)", ctx.client.parse_links(change["logparams"]["0"]))
    content = _("[{author}]({author_url}) created the Cargo table \"{table}\"").format(author=author,
                                                                                       author_url=author_url,
                                                                                       table=table)
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)


# cargo/recreatetable - Recreating a Cargo table


@formatter.embed(event="cargo/recreatetable")
def embed_cargo_recreatetable(ctx: Context, change: dict):
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change)
    table = re.search(r"\[(.*?)]\(<(.*?)>\)", ctx.client.parse_links(change["logparams"]["0"]))
    embed["url"] = table.group(2)
    embed["title"] = _("Recreated the Cargo table \"{table}\"").format(table=table.group(1))
    return embed


@formatter.compact(event="cargo/recreatetable")
def compact_cargo_recreatetable(ctx: Context, change: dict):
    author, author_url = compact_author(ctx, change)
    table = re.search(r"\[(.*?)]\(<(.*?)>\)", ctx.client.parse_links(change["logparams"]["0"]))
    content = _("[{author}]({author_url}) recreated the Cargo table \"{table}\"").format(author=author,
                                                                                         author_url=author_url,
                                                                                         table=table)
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)


# cargo/replacetable - Replacing a Cargo table


@formatter.embed(event="cargo/replacetable")
def embed_cargo_replacetable(ctx: Context, change: dict):
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change)
    table = re.search(r"\[(.*?)]\(<(.*?)>\)", ctx.client.parse_links(change["logparams"]["0"]))
    embed["url"] = table.group(2)
    embed["title"] = _("Replaced the Cargo table \"{table}\"").format(table=table.group(1))
    return embed


@formatter.compact(event="cargo/replacetable")
def compact_cargo_replacetable(ctx: Context, change: dict):
    author, author_url = compact_author(ctx, change)
    table = re.search(r"\[(.*?)]\(<(.*?)>\)", ctx.client.parse_links(change["logparams"]["0"]))
    content = _("[{author}]({author_url}) replaced the Cargo table \"{table}\"").format(author=author,
                                                                                        author_url=author_url,
                                                                                        table=table)
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)


# cargo/deletetable - Deleting a table in Cargo


@formatter.embed(event="cargo/deletetable")
def embed_cargo_deletetable(ctx: Context, change: dict):
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change)
    embed["url"] = create_article_path("Special:CargoTables")
    embed["title"] = _("Deleted the Cargo table \"{table}\"").format(table=sanitize_to_markdown(change["logparams"]["0"]))
    return embed


@formatter.compact(event="cargo/deletetable")
def compact_cargo_deletetable(ctx: Context, change: dict):
    author, author_url = compact_author(ctx, change)
    content = _("[{author}]({author_url}) deleted the Cargo table \"{table}\"").format(author=author,
                                                                                       author_url=author_url,
                                                                                       table=sanitize_to_markdown(change["logparams"]["0"]))
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)
