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

from src.discord.message import DiscordMessage
from src.api import formatter
from src.i18n import formatters_i18n
from src.api.context import Context
from src.api.util import embed_helper, compact_author, create_article_path, sanitize_to_markdown, sanitize_to_url, compact_summary

_ = formatters_i18n.gettext
ngettext = formatters_i18n.ngettext


# ManageWiki - https://www.mediawiki.org/wiki/Special:MyLanguage/Extension:ManageWiki
# managewiki/settings - Changing wiki settings

@formatter.embed(event="managewiki/settings")
def embed_managewiki_settings(ctx: Context, change: dict):
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change)
    embed["url"] = create_article_path(sanitize_to_url(change["title"]))
    embed["title"] = _("Changed wiki settings")
    if change["logparams"].get("changes", ""):
        embed.add_field("Setting", sanitize_to_markdown(change["logparams"].get("changes")))
    return embed


@formatter.compact(event="managewiki/settings")
def compact_managewiki_settings(ctx: Context, change: dict):
    author, author_url = compact_author(ctx, change)
    parsed_comment = compact_summary(ctx)
    content = _("[{author}]({author_url}) changed wiki settings{reason}".format(author=author, author_url=author_url, reason=parsed_comment))
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)

# managewiki/delete - Deleting a wiki


@formatter.embed(event="managewiki/delete")
def embed_managewiki_delete(ctx: Context, change: dict):
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change)
    embed["url"] = create_article_path(sanitize_to_url(change["title"]))
    embed["title"] = _("Deleted a \"{wiki}\" wiki").format(wiki=change["logparams"].get("wiki", _("Unknown")))
    return embed


@formatter.compact(event="managewiki/delete")
def compact_managewiki_delete(ctx: Context, change: dict):
    author, author_url = compact_author(ctx, change)
    parsed_comment = compact_summary(ctx)
    content = _("[{author}]({author_url}) deleted a wiki *{wiki_name}*{comment}").format(author=author,
                                                                                         author_url=author_url,
                                                                                         wiki_name=change[
                                                                                             "logparams"].get("wiki",
                                                                                                              _("Unknown")),
                                                                                         comment=parsed_comment)
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)

# managewiki/delete-group - Deleting a group


@formatter.embed(event="managewiki/delete-group")
def embed_managewiki_delete_group(ctx: Context, change: dict) -> DiscordMessage:
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change)
    embed["url"] = create_article_path(sanitize_to_url(change["title"]))
    group = change["title"].split("/")[-1]
    embed["title"] = _("Deleted a \"{group}\" user group").format(wiki=group)
    return embed


@formatter.compact(event="managewiki/delete-group")
def compact_managewiki_delete_group(ctx: Context, change: dict) -> DiscordMessage:
    author, author_url = compact_author(ctx, change)
    parsed_comment = compact_summary(ctx)
    group = change["title"].split("/")[-1]
    content = _("[{author}]({author_url}) deleted a usergroup *{group}*{comment}").format(author=author,
                                                                                         author_url=author_url,
                                                                                         group=group,
                                                                                         comment=parsed_comment)
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)

# managewiki/lock - Locking a wiki


@formatter.embed(event="managewiki/lock")
def embed_managewiki_lock(ctx: Context, change: dict):
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change)
    embed["url"] = create_article_path(sanitize_to_url(change["title"]))
    embed["title"] = _("Locked a \"{wiki}\" wiki").format(wiki=change["logparams"].get("wiki", _("Unknown")))
    return embed


@formatter.compact(event="managewiki/lock")
def compact_managewiki_lock(ctx: Context, change: dict):
    author, author_url = compact_author(ctx, change)
    parsed_comment = compact_summary(ctx)
    content = _("[{author}]({author_url}) locked a wiki *{wiki_name}*{comment}").format(
        author=author, author_url=author_url, wiki_name=change["logparams"].get("wiki", _("Unknown")),
        comment=parsed_comment)
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)

# managewiki/namespaces - Modirying a wiki namespace


@formatter.embed(event="managewiki/namespaces")
def embed_managewiki_namespaces(ctx: Context, change: dict):
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change)
    embed["url"] = create_article_path(sanitize_to_url(change["title"]))
    embed["title"] = _("Modified \"{namespace_name}\" namespace").format(
        namespace_name=change["logparams"].get("namespace", _("Unknown")))
    embed.add_field(_('Wiki'), change["logparams"].get("wiki", _("Unknown")))
    return embed


@formatter.compact(event="managewiki/namespaces")
def compact_managewiki_namespaces(ctx: Context, change: dict):
    author, author_url = compact_author(ctx, change)
    parsed_comment = compact_summary(ctx)
    content = _("[{author}]({author_url}) modified namespace *{namespace_name}* on *{wiki_name}*{comment}").format(
        author=author, author_url=author_url, namespace_name=change["logparams"].get("namespace", _("Unknown")),
        wiki_name=change["logparams"].get("wiki", _("Unknown")), comment=parsed_comment)
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)

# managewiki/namespaces-delete - Deleteing a namespace


@formatter.embed(event="managewiki/namespaces-delete")
def embed_managewiki_namespaces_delete(ctx: Context, change: dict):
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change)
    embed["url"] = create_article_path(sanitize_to_url(change["title"]))
    embed["title"] = _("Deleted a \"{namespace_name}\" namespace").format(
        namespace_name=change["logparams"].get("namespace", _("Unknown")))
    embed.add_field(_('Wiki'), change["logparams"].get("wiki", _("Unknown")))
    return embed


@formatter.compact(event="managewiki/namespaces-delete")
def compact_managewiki_namespaces_delete(ctx: Context, change: dict):
    author, author_url = compact_author(ctx, change)
    parsed_comment = compact_summary(ctx)
    content = _(
        "[{author}]({author_url}) deleted a namespace *{namespace_name}* on *{wiki_name}*{comment}").format(
        author=author, author_url=author_url,
        namespace_name=change["logparams"].get("namespace", _("Unknown")),
        wiki_name=change["logparams"].get("wiki", _("Unknown")), comment=parsed_comment)
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)

# managewiki/rights - Modifying user groups


@formatter.embed(event="managewiki/rights")
def embed_managewiki_rights(ctx: Context, change: dict):
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change)
    embed["url"] = create_article_path(sanitize_to_url(change["title"]))
    group_name = change["title"].split("/permissions/", 1)[1]
    embed["title"] = _("Modified \"{usergroup_name}\" usergroup").format(usergroup_name=group_name)
    return embed


@formatter.compact(event="managewiki/rights")
def compact_managewiki_rights(ctx: Context, change: dict):
    author, author_url = compact_author(ctx, change)
    parsed_comment = compact_summary(ctx)
    group_name = change["title"].split("/permissions/", 1)[1]
    content = _("[{author}]({author_url}) modified user group *{group_name}*{comment}").format(
        author=author, author_url=author_url, group_name=group_name, comment=parsed_comment
    )
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)

# managewiki/undelete - Restoring a wiki


@formatter.embed(event="managewiki/undelete")
def embed_managewiki_undelete(ctx: Context, change: dict):
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change)
    embed["url"] = create_article_path(sanitize_to_url(change["title"]))
    embed["title"] = _("Undeleted a \"{wiki}\" wiki").format(wiki=change["logparams"].get("wiki", _("Unknown")))
    return embed


@formatter.compact(event="managewiki/undelete")
def compact_managewiki_undelete(ctx: Context, change: dict):
    author, author_url = compact_author(ctx, change)
    parsed_comment = compact_summary(ctx)
    content = _("[{author}]({author_url}) undeleted a wiki *{wiki_name}*{comment}").format(
        author=author, author_url=author_url, wiki_name=change["logparams"].get("wiki", _("Unknown")),
        comment=parsed_comment
    )
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)

# managewiki/unlock - Unlocking a wiki


@formatter.embed(event="managewiki/unlock")
def embed_managewiki_unlock(ctx: Context, change: dict):
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change)
    embed["url"] = create_article_path(sanitize_to_url(change["title"]))
    embed["title"] = _("Unlocked a \"{wiki}\" wiki").format(wiki=change["logparams"].get("wiki", _("Unknown")))
    return embed


@formatter.compact(event="managewiki/unlock")
def compact_managewiki_unlock(ctx: Context, change: dict):
    author, author_url = compact_author(ctx, change)
    parsed_comment = compact_summary(ctx)
    content = _("[{author}]({author_url}) unlocked a wiki *{wiki_name}*{comment}").format(
        author=author, author_url=author_url, wiki_name=change["logparams"].get("wiki", _("Unknown")),
        comment=parsed_comment
    )
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)
