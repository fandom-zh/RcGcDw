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
from src.api.util import embed_helper, compact_author, create_article_path, sanitize_to_markdown, sanitize_to_url, \
    clean_link

_ = formatters_i18n.gettext
ngettext = formatters_i18n.ngettext


# SpriteSheet - https://www.mediawiki.org/wiki/Extension:SpriteSheet
# sprite/sprite - Editing a sprite


@formatter.embed(event="sprite/sprite")
def embed_sprite_sprite(ctx: Context, change: dict):
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change)
    embed["url"] = create_article_path(sanitize_to_url(change["title"]))
    embed["title"] = _("Edited the sprite for {article}").format(article=sanitize_to_markdown(change["title"]))
    return embed


@formatter.compact(event="sprite/sprite")
def compact_sprite_sprite(ctx: Context, change: dict):
    author, author_url = compact_author(ctx, change)
    link = clean_link(create_article_path(sanitize_to_url(change["title"])))
    content = _("[{author}]({author_url}) edited the sprite for [{article}]({article_url})").format(author=author,
                                                                                                    author_url=author_url,
                                                                                                    article=sanitize_to_markdown(change[
                                                                                                        "title"]),
                                                                                                    article_url=link)
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)

# sprite/sheet - Creating a sprite sheet


@formatter.embed(event="sprite/sheet")
def embed_sprite_sheet(ctx: Context, change: dict):
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change)
    embed["url"] = create_article_path(sanitize_to_url(change["title"]))
    embed["title"] = _("Created the sprite sheet for {article}").format(article=sanitize_to_markdown(change["title"]))
    return embed


@formatter.compact(event="sprite/sheet")
def compact_sprite_sheet(ctx: Context, change: dict):
    author, author_url = compact_author(ctx, change)
    link = clean_link(create_article_path(sanitize_to_url(change["title"])))
    content = _("[{author}]({author_url}) created the sprite sheet for [{article}]({article_url})").format(author=author, author_url=author_url, article=sanitize_to_markdown(change["title"]), article_url=link)
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)

# sprite/slice - Editing a slice


@formatter.embed(event="sprite/slice")
def embed_sprite_slice(ctx: Context, change: dict):
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change)
    embed["url"] = create_article_path(sanitize_to_url(change["title"]))
    embed["title"] = _("Edited the slice for {article}").format(article=sanitize_to_markdown(change["title"]))
    return embed

@formatter.compact(event="sprite/slice")
def compact_sprite_slice(ctx: Context, change: dict):
    author, author_url = compact_author(ctx, change)
    link = clean_link(create_article_path(sanitize_to_url(change["title"])))
    content = _("[{author}]({author_url}) edited the slice for [{article}]({article_url})").format(author=author,
                                                                                                   author_url=author_url,
                                                                                                   article=sanitize_to_markdown(change[
                                                                                                       "title"]),
                                                                                                   article_url=link)
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)
