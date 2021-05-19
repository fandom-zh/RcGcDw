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
from src.api.util import embed_helper, clean_link, compact_author, create_article_path, sanitize_to_url, compact_summary

_ = formatters_i18n.gettext
ngettext = formatters_i18n.ngettext


# Interwiki - https://www.mediawiki.org/wiki/Extension:Interwiki
# interwiki/iw_add - Added entry to interwiki table


@formatter.embed(event="interwiki/iw_add", mode="embed")
def embed_interwiki_iw_add(ctx: Context, change: dict) -> DiscordMessage:
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change, set_desc=False)
    embed["url"] = create_article_path("Special:Interwiki")
    embed["title"] = _("Added an entry to the interwiki table")
    embed["description"] = _("Prefix: {prefix}, website: {website} | {desc}").format(desc=ctx.parsedcomment,
                                                                                     prefix=change["logparams"]['0'],
                                                                                     website=change["logparams"]['1'])
    return embed


@formatter.compact(event="interwiki/iw_add")
def compact_interwiki_iw_add(ctx: Context, change: dict) -> DiscordMessage:
    author, author_url = compact_author(ctx, change)
    link = clean_link(create_article_path("Special:Interwiki"))
    parsed_comment = compact_summary(ctx)
    content = _(
        "[{author}]({author_url}) added an entry to the [interwiki table]({table_url}) pointing to {website} with {prefix} prefix").format(
        author=author, author_url=author_url, desc=parsed_comment, prefix=change["logparams"]['0'],
        website=change["logparams"]['1'], table_url=link)
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)


# interwiki/iw_edit - Editing interwiki entry


@formatter.embed(event="interwiki/iw_edit", mode="embed")
def embed_interwiki_iw_edit(ctx: Context, change: dict) -> DiscordMessage:
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change, set_desc=False)
    embed["url"] = create_article_path("Special:Interwiki")
    embed["title"] = _("Edited an entry in interwiki table")
    embed["description"] = _("Prefix: {prefix}, website: {website} | {desc}").format(desc=ctx.parsedcomment,
                                                                                     prefix=change["logparams"]['0'],
                                                                                     website=change["logparams"]['1'])
    return embed


@formatter.compact(event="interwiki/iw_edit")
def compact_interwiki_iw_edit(ctx: Context, change: dict) -> DiscordMessage:
    author, author_url = compact_author(ctx, change)
    link = clean_link(create_article_path("Special:Interwiki"))
    parsed_comment = compact_summary(ctx)
    content = _(
        "[{author}]({author_url}) edited an entry in [interwiki table]({table_url}) pointing to {website} with {prefix} prefix").format(
        author=author, author_url=author_url, desc=parsed_comment, prefix=change["logparams"]['0'],
        website=change["logparams"]['1'], table_url=link)
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)


# interwiki/iw_delete - Deleting interwiki entry


@formatter.embed(event="interwiki/iw_delete", mode="embed")
def embed_interwiki_iw_delete(ctx: Context, change: dict) -> DiscordMessage:
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change, set_desc=False)
    embed["url"] = create_article_path("Special:Interwiki")
    embed["title"] = _("Deleted an entry in interwiki table")
    embed["description"] = _("Prefix: {prefix} | {desc}").format(desc=ctx.parsedcomment,
                                                                 prefix=change["logparams"]['0'])
    return embed


@formatter.compact(event="interwiki/iw_delete")
def compact_interwiki_iw_delete(ctx: Context, change: dict) -> DiscordMessage:
    author, author_url = compact_author(ctx, change)
    link = clean_link(create_article_path("Special:Interwiki"))
    parsed_comment = compact_summary(ctx)
    content = _("[{author}]({author_url}) deleted an entry in [interwiki table]({table_url}){desc}").format(
        author=author,
        author_url=author_url,
        table_url=link,
        desc=parsed_comment)

    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)
