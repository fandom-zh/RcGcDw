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
from src.configloader import settings
from src.discord.message import DiscordMessage
from src.api import formatter
from src.i18n import formatters_i18n
from src.api.context import Context
from src.api.util import embed_helper, clean_link, compact_author, create_article_path, sanitize_to_markdown, sanitize_to_url
from src.misc import profile_field_name

_ = formatters_i18n.gettext
ngettext = formatters_i18n.ngettext


# CurseProfile - https://help.fandom.com/wiki/Extension:CurseProfile
# curseprofile/profile-edited - Editing user profile


@formatter.embed(event="curseprofile/profile-edited")
def embed_curseprofile_profile_edited(ctx: Context, change: dict) -> DiscordMessage:
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change)
    target_user = change["title"].split(':', 1)[1]
    if target_user != change["user"]:
        embed["title"] = _("Edited {target}'s profile").format(target=sanitize_to_markdown(target_user))
    else:
        embed["title"] = _("Edited their own profile")
    if ctx.parsedcomment is None:  # If the field is empty
        embed["description"] = _("Cleared the {field} field").format(field=profile_field_name(change["logparams"]['4:section'], True))
    else:
        embed["description"] = _("{field} field changed to: {desc}").format(field=profile_field_name(change["logparams"]['4:section'], True), desc=ctx.parsedcomment)
    embed["url"] = create_article_path("UserProfile:" + sanitize_to_url(target_user))
    return embed


@formatter.compact(event="curseprofile/profile-edited")
def compact_curseprofile_profile_edited(ctx: Context, change: dict) -> DiscordMessage:
    author, author_url = compact_author(ctx, change)
    target_user = change["title"].split(':', 1)[1]
    link = clean_link(create_article_path("UserProfile:" + sanitize_to_url(target_user)))
    if target_user != author:
        if ctx.parsedcomment is None:  # If the field is empty
            edit_clear_message = _("[{author}]({author_url}) cleared the {field} on [{target}]({target_url})'s profile.")
        else:
            edit_clear_message = _("[{author}]({author_url}) edited the {field} on [{target}]({target_url})'s profile. *({desc})*")
        content = edit_clear_message.format(author=author, author_url=author_url, target=sanitize_to_markdown(target_user), target_url=link,
            field=profile_field_name(change["logparams"]['4:section'], False), desc=ctx.parsedcomment)
    else:
        if ctx.parsedcomment is None:  # If the field is empty
            edit_clear_message = _("[{author}]({author_url}) cleared the {field} on [their own]({target_url}) profile.")
        else:
            edit_clear_message = _("[{author}]({author_url}) edited the {field} on [their own]({target_url}) profile. *({desc})*")
        content = edit_clear_message.format(author=author, author_url=author_url, target_url=link,
            field=profile_field_name(change["logparams"]['4:section'], False), desc=ctx.parsedcomment)
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)


# curseprofile/comment-created - Creating comment on user profile


@formatter.embed(event="curseprofile/comment-created")
def embed_curseprofile_comment_created(ctx: Context, change: dict) -> DiscordMessage:
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change)
    target_user = change["title"].split(':', 1)[1]
    if target_user != change["user"]:
        embed["title"] = _("Left a comment on {target}'s profile").format(target=sanitize_to_markdown(target_user))
    else:
        embed["title"] = _("Left a comment on their own profile")
    if settings["appearance"]["embed"]["show_edit_changes"]:
        embed["description"] = ctx.client.pull_curseprofile_comment(change["logparams"]["4:comment_id"])
    embed["url"] = create_article_path("Special:CommentPermalink/{commentid}".format(commentid=change["logparams"]["4:comment_id"]))
    return embed


@formatter.compact(event="curseprofile/comment-created")
def compact_curseprofile_comment_created(ctx: Context, change: dict) -> DiscordMessage:
    author, author_url = compact_author(ctx, change)
    target_user = change["title"].split(':', 1)[1]
    link = clean_link(create_article_path("Special:CommentPermalink/{commentid}".format(commentid=change["logparams"]["4:comment_id"])))
    if target_user != author:
        content = _("[{author}]({author_url}) left a [comment]({comment}) on {target}'s profile.").format(
            author=author, author_url=author_url, comment=link, target=sanitize_to_markdown(target_user))
    else:
        content = _("[{author}]({author_url}) left a [comment]({comment}) on their own profile.").format(author=author, author_url=author_url, comment=link)
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)


# curseprofile/comment-edited - Editing comment on user profile


@formatter.embed(event="curseprofile/comment-edited")
def embed_curseprofile_comment_edited(ctx: Context, change: dict) -> DiscordMessage:
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change)
    target_user = change["title"].split(':', 1)[1]
    if target_user != change["user"]:
        embed["title"] = _("Edited a comment on {target}'s profile").format(target=sanitize_to_markdown(target_user))
    else:
        embed["title"] = _("Edited a comment on their own profile")
    if settings["appearance"]["embed"]["show_edit_changes"]:
        embed["description"] = ctx.client.pull_curseprofile_comment(change["logparams"]["4:comment_id"])
    embed["url"] = create_article_path("Special:CommentPermalink/{commentid}".format(commentid=change["logparams"]["4:comment_id"]))
    return embed


@formatter.compact(event="curseprofile/comment-edited")
def compact_curseprofile_comment_edited(ctx: Context, change: dict) -> DiscordMessage:
    author, author_url = compact_author(ctx, change)
    target_user = change["title"].split(':', 1)[1]
    link = clean_link(create_article_path("Special:CommentPermalink/{commentid}".format(commentid=change["logparams"]["4:comment_id"])))
    if target_user != author:
        content = _("[{author}]({author_url}) edited a [comment]({comment}) on {target}'s profile.").format(
            author=author, author_url=author_url, comment=link, target=sanitize_to_markdown(target_user))
    else:
        content = _("[{author}]({author_url}) edited a [comment]({comment}) on their own profile.").format(author=author, author_url=author_url, comment=link)
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)


# curseprofile/comment-replied - Replying to comment on user profile


@formatter.embed(event="curseprofile/comment-replied")
def embed_curseprofile_comment_replied(ctx: Context, change: dict) -> DiscordMessage:
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change)
    target_user = change["title"].split(':', 1)[1]
    if target_user != change["user"]:
        embed["title"] = _("Replied to a comment on {target}'s profile").format(target=sanitize_to_markdown(target_user))
    else:
        embed["title"] = _("Replied to a comment on their own profile")
    if settings["appearance"]["embed"]["show_edit_changes"]:
        embed["description"] = ctx.client.pull_curseprofile_comment(change["logparams"]["4:comment_id"])
    embed["url"] = create_article_path("Special:CommentPermalink/{commentid}".format(commentid=change["logparams"]["4:comment_id"]))
    return embed


@formatter.compact(event="curseprofile/comment-replied")
def compact_curseprofile_comment_replied(ctx: Context, change: dict) -> DiscordMessage:
    author, author_url = compact_author(ctx, change)
    target_user = change["title"].split(':', 1)[1]
    link = clean_link(create_article_path("Special:CommentPermalink/{commentid}".format(commentid=change["logparams"]["4:comment_id"])))
    if target_user != author:
        content = _("[{author}]({author_url}) replied to a [comment]({comment}) on {target}'s profile.").format(
            author=author, author_url=author_url, comment=link, target=sanitize_to_markdown(target_user))
    else:
        content = _("[{author}]({author_url}) replied to a [comment]({comment}) on their own profile.").format(author=author, author_url=author_url, comment=link)
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)


# curseprofile/comment-deleted - Deleting comment on user profile


@formatter.embed(event="curseprofile/comment-deleted")
def embed_curseprofile_comment_deleted(ctx: Context, change: dict) -> DiscordMessage:
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change)
    target_user = change["title"].split(':', 1)[1]
    if target_user != change["user"]:
        embed["title"] = _("Deleted a comment on {target}'s profile").format(target=sanitize_to_markdown(target_user))
    else:
        embed["title"] = _("Deleted a comment on their own profile")
    if ctx.parsedcomment is not None:
        embed["description"] = ctx.parsedcomment
    if "4:comment_id" in change["logparams"]:
        embed["url"] = create_article_path("Special:CommentPermalink/{commentid}".format(commentid=change["logparams"]["4:comment_id"]))
    else:
        embed["url"] = create_article_path("UserProfile:" + sanitize_to_url(target_user))
    return embed


@formatter.compact(event="curseprofile/comment-deleted")
def compact_curseprofile_comment_deleted(ctx: Context, change: dict) -> DiscordMessage:
    author, author_url = compact_author(ctx, change)
    target_user = change["title"].split(':', 1)[1]
    if "4:comment_id" in change["logparams"]:
        link = clean_link(create_article_path("Special:CommentPermalink/{commentid}".format(commentid=change["logparams"]["4:comment_id"])))
    else:
        link = clean_link(create_article_path("UserProfile:" + sanitize_to_url(target_user)))
    parsed_comment = "" if ctx.parsedcomment is None else " *(" + ctx.parsedcomment + ")*"
    if target_user != author:
        content = _("[{author}]({author_url}) deleted a [comment]({comment}) on {target}'s profile.{reason}").format(
            author=author, author_url=author_url, comment=link, target=sanitize_to_markdown(target_user), reason=parsed_comment)
    else:
        content = _("[{author}]({author_url}) deleted a [comment]({comment}) on their own profile.{reason}").format(
            author=author, author_url=author_url, comment=link, reason=parsed_comment)
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)


# curseprofile/comment-purged - Purging comment on user profile


@formatter.embed(event="curseprofile/comment-purged")
def embed_curseprofile_comment_purged(ctx: Context, change: dict) -> DiscordMessage:
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change)
    target_user = change["title"].split(':', 1)[1]
    if target_user != change["user"]:
        embed["title"] = _("Purged a comment on {target}'s profile").format(target=sanitize_to_markdown(target_user))
    else:
        embed["title"] = _("Purged a comment on their own profile")
    if ctx.parsedcomment is not None:
        embed["description"] = ctx.parsedcomment
    embed["url"] = create_article_path("UserProfile:" + sanitize_to_url(target_user))
    return embed


@formatter.compact(event="curseprofile/comment-purged")
def compact_curseprofile_comment_purged(ctx: Context, change: dict) -> DiscordMessage:
    author, author_url = compact_author(ctx, change)
    target_user = change["title"].split(':', 1)[1]
    link = clean_link(create_article_path("UserProfile:" + sanitize_to_url(target_user)))
    parsed_comment = "" if ctx.parsedcomment is None else " *(" + ctx.parsedcomment + ")*"
    if target_user != author:
        content = _("[{author}]({author_url}) purged a comment on [{target}]({link})'s profile.{reason}").format(
            author=author, author_url=author_url, link=link, target=sanitize_to_markdown(target_user), reason=parsed_comment)
    else:
        content = _("[{author}]({author_url}) purged a comment on [their own]({link}) profile.{reason}").format(author=author, author_url=author_url, link=link)
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content, reason=parsed_comment)
