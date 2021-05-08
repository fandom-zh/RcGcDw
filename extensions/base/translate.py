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
from src.i18n import rc_formatters
from src.api.context import Context
from src.api.util import embed_helper, compact_author, create_article_path, sanitize_to_markdown, sanitize_to_url, \
    clean_link

_ = rc_formatters.gettext
ngettext = rc_formatters.ngettext

# I cried when I realized I have to migrate Translate extension logs, but this way I atone for my countless sins
# Translate - https://www.mediawiki.org/wiki/Extension:Translate
# pagetranslation/mark - Marking a page for translation


@formatter.embed(event="pagetranslation/mark")
def embed_pagetranslation_mark(ctx: Context, change: dict):
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change)
    link = create_article_path(sanitize_to_url(change["title"]))
    if "?" in link:
        embed["url"] = link + "&oldid={}".format(change["logparams"]["revision"])
    else:
        embed["url"] = link + "?oldid={}".format(change["logparams"]["revision"])
    embed["title"] = _("Marked \"{article}\" for translation").format(article=sanitize_to_markdown(change["title"]))
    return embed


@formatter.compact(event="pagetranslation/mark")
def compact_pagetranslation_mark(ctx: Context, change: dict):
    author, author_url = compact_author(ctx, change)
    link = create_article_path(sanitize_to_url(change["title"]))
    if "?" in link:
        link = link + "&oldid={}".format(change["logparams"]["revision"])
    else:
        link = link + "?oldid={}".format(change["logparams"]["revision"])
    link = clean_link(link)
    parsed_comment = "" if ctx.parsedcomment is None else " *(" + ctx.parsedcomment + ")*"
    content = _("[{author}]({author_url}) marked [{article}]({article_url}) for translation{comment}").format(
        author=author, author_url=author_url,
        article=change["title"], article_url=link,
        comment=parsed_comment
    )
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)

# pagetranslation/unmark - Removing a page from translation system


@formatter.embed(event="pagetranslation/unmark")
def embed_pagetranslation_unmark(ctx: Context, change: dict):
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change)
    embed["url"] = create_article_path(sanitize_to_url(change["title"]))
    embed["title"] = _("Removed \"{article}\" from the translation system").format(article=sanitize_to_markdown(change["title"]))
    return embed


@formatter.compact(event="pagetranslation/unmark")
def compact_pagetranslation_unmark(ctx: Context, change: dict):
    author, author_url = compact_author(ctx, change)
    parsed_comment = "" if ctx.parsedcomment is None else " *(" + ctx.parsedcomment + ")*"
    link = clean_link(create_article_path(sanitize_to_url(change["title"])))
    content = _(
        "[{author}]({author_url}) removed [{article}]({article_url}) from the translation system{comment}").format(
        author=author, author_url=author_url,
        article=sanitize_to_markdown(change["title"]), article_url=link,
        comment=parsed_comment
    )
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)

# pagetranslation/moveok - Completed moving translation page


@formatter.embed(event="pagetranslation/moveok")
def embed_pagetranslation_moveok(ctx: Context, change: dict):
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change)
    embed["url"] = create_article_path(sanitize_to_url(change["logparams"]["target"]))
    embed["title"] = _("Completed moving translation pages from \"{article}\" to \"{target}\"").format(
        article=sanitize_to_markdown(change["title"]), target=sanitize_to_markdown(change["logparams"]["target"]))
    return embed


@formatter.compact(event="pagetranslation/moveok")
def compact_pagetranslation_moveok(ctx: Context, change: dict):
    author, author_url = compact_author(ctx, change)
    parsed_comment = "" if ctx.parsedcomment is None else " *(" + ctx.parsedcomment + ")*"
    link = clean_link(create_article_path(sanitize_to_url(change["logparams"]["target"])))
    content = _(
        "[{author}]({author_url}) completed moving translation pages from *{article}* to [{target}]({target_url}){comment}").format(
        author=author, author_url=author_url,
        article=sanitize_to_markdown(change["title"]), target=sanitize_to_markdown(change["logparams"]["target"]),
        target_url=link, comment=parsed_comment
    )
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)

# pagetranslation/movenok - Failed while moving translation page


@formatter.embed(event="pagetranslation/movenok")
def embed_pagetranslation_movenok(ctx: Context, change: dict):
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change)
    embed["url"] = create_article_path(sanitize_to_url(change["title"]))
    embed["title"] = _("Encountered a problem while moving \"{article}\" to \"{target}\"").format(
        article=sanitize_to_markdown(change["title"]), target=sanitize_to_markdown(change["logparams"]["target"]))
    return embed


@formatter.compact(event="pagetranslation/movenok")
def compact_pagetranslation_movenok(ctx: Context, change: dict):
    author, author_url = compact_author(ctx, change)
    parsed_comment = "" if ctx.parsedcomment is None else " *(" + ctx.parsedcomment + ")*"
    link = clean_link(create_article_path(sanitize_to_url(change["title"])))
    target_url = clean_link(create_article_path(sanitize_to_url(change["logparams"]["target"])))
    content = _(
        "[{author}]({author_url}) encountered a problem while moving [{article}]({article_url}) to [{target}]({target_url}){comment}").format(
        author=author, author_url=author_url,
        article=sanitize_to_markdown(change["title"]), article_url=link,
        target=sanitize_to_markdown(change["logparams"]["target"]), target_url=target_url,
        comment=parsed_comment
    )
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)

# pagetranslation/deletefnok - Failure in deletion of translatable page


@formatter.embed(event="pagetranslation/deletefnok")
def embed_pagetranslation_deletefnok(ctx: Context, change: dict):
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change)
    embed["url"] = create_article_path(sanitize_to_url(change["title"]))
    embed["title"] = _("Failed to delete \"{article}\" which belongs to translatable page \"{target}\"").format(
        article=sanitize_to_markdown(change["title"]), target=sanitize_to_markdown(change["logparams"]["target"]))
    return embed


@formatter.compact(event="pagetranslation/deletefnok")
def compact_pagetranslation_deletefnok(ctx: Context, change: dict):
    author, author_url = compact_author(ctx, change)
    parsed_comment = "" if ctx.parsedcomment is None else " *(" + ctx.parsedcomment + ")*"
    link = clean_link(create_article_path(sanitize_to_url(change["title"])))
    target_url = clean_link(create_article_path(sanitize_to_url(change["logparams"]["target"])))
    content = _(
        "[{author}]({author_url}) failed to delete [{article}]({article_url}) which belongs to translatable page [{target}]({target_url}){comment}").format(
        author=author, author_url=author_url,
        article=sanitize_to_markdown(change["title"]), article_url=link,
        target=sanitize_to_markdown(change["logparams"]["target"]), target_url=target_url,
        comment=parsed_comment
    )
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)

# pagetranslation/deletelok - Completion in deleting a page?


@formatter.embed(event="pagetranslation/deletelok")
def embed_pagetranslation_deletelok(ctx: Context, change: dict):
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change)
    embed["url"] = create_article_path(sanitize_to_url(change["title"]))
    embed["title"] = _("Completed deletion of translation page \"{article}\"").format(
        article=sanitize_to_markdown(change["title"]))
    return embed


@formatter.compact(event="pagetranslation/deletelok")
def compact_pagetranslation_deletelok(ctx: Context, change: dict):
    author, author_url = compact_author(ctx, change)
    parsed_comment = "" if ctx.parsedcomment is None else " *(" + ctx.parsedcomment + ")*"
    link = clean_link(create_article_path(sanitize_to_url(change["title"])))
    content = _(
        "[{author}]({author_url}) completed deletion of translation page [{article}]({article_url}){comment}").format(
        author=author, author_url=author_url,
        article=sanitize_to_markdown(change["title"]), article_url=link,
        comment=parsed_comment
    )
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)

# pagetranslation/deletelnok - Failure in deletion of article belonging to a translation page


@formatter.embed(event="pagetranslation/deletelnok")
def embed_pagetranslation_deletelnok(ctx: Context, change: dict):
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change)
    embed["url"] = create_article_path(sanitize_to_url(change["title"]))
    embed["title"] = _("Failed to delete \"{article}\" which belongs to translation page \"{target}\"").format(
        article=sanitize_to_markdown(change["title"]), target=sanitize_to_markdown(change["logparams"]["target"]))
    return embed


@formatter.compact(event="pagetranslation/deletelnok")
def compact_pagetranslation_deletelnok(ctx: Context, change: dict):
    author, author_url = compact_author(ctx, change)
    parsed_comment = "" if ctx.parsedcomment is None else " *(" + ctx.parsedcomment + ")*"
    link = clean_link(create_article_path(sanitize_to_url(change["title"])))
    target_url = clean_link(create_article_path(sanitize_to_url(change["logparams"]["target"])))
    content = _(
        "[{author}]({author_url}) failed to delete [{article}]({article_url}) which belongs to translation page [{target}]({target_url}){comment}").format(
        author=author, author_url=author_url,
        article=sanitize_to_markdown(change["title"]), article_url=link,
        target=sanitize_to_markdown(change["logparams"]["target"]), target_url=target_url,
        comment=parsed_comment
    )
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)

