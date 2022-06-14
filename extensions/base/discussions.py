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

# Discussions - Custom Fandom technology which apparently doesn't have any documentation or homepage, not even open-source, go figure

import json
import datetime, logging
import gettext
from urllib.parse import quote_plus

from src.configloader import settings
from src.api.util import create_article_path, clean_link, sanitize_to_markdown
from src.api.context import Context
from src.discord.queue import send_to_discord
from src.discord.message import DiscordMessage, DiscordMessageMetadata
from src.api import formatter
from src.i18n import formatters_i18n

_ = formatters_i18n.gettext


logger = logging.getLogger("rcgcdw.discussion_formatter")


class DiscussionsFromHellParser:
    """This class converts fairly convoluted Fandom jsonModal of a discussion post into Markdown formatted usable thing.
    Takes string, returns string. Kudos to MarkusRost for allowing me to implement this formatter based on his code in Wiki-Bot."""

    def __init__(self, post):
        self.post = post
        self.jsonModal = json.loads(post.get("jsonModel", "{}"))
        self.markdown_text = ""
        self.item_num = 1
        self.image_last = None

    def parse(self) -> str:
        """Main parsing logic"""
        self.parse_content(self.jsonModal["content"])
        if len(self.markdown_text) > 2000:
            self.markdown_text = self.markdown_text[0:2000] + "…"
        return self.markdown_text

    def parse_content(self, content, ctype=None):
        self.image_last = None
        for item in content:
            if ctype == "bulletList":
                self.markdown_text += "\t• "
            if ctype == "orderedList":
                self.markdown_text += "\t{num}. ".format(num=self.item_num)
                self.item_num += 1
            if item["type"] == "text":
                if "marks" in item:
                    prefix, suffix = self.convert_marks(item["marks"])
                    self.markdown_text = "{old}{pre}{text}{suf}".format(old=self.markdown_text, pre=prefix,
                                                                        text=sanitize_to_markdown(item["text"]),
                                                                        suf=suffix)
                else:
                    if ctype == "code_block":
                        self.markdown_text += item["text"]  # ignore formatting on preformatted text which cannot have additional formatting anyways
                    else:
                        self.markdown_text += sanitize_to_markdown(item["text"])
            elif item["type"] == "paragraph":
                if "content" in item:
                    self.parse_content(item["content"], item["type"])
                self.markdown_text += "\n"
            elif item["type"] == "openGraph":
                if not item["attrs"]["wasAddedWithInlineLink"]:
                    self.markdown_text = "{old}{link}\n".format(old=self.markdown_text, link=item["attrs"]["url"])
            elif item["type"] == "image":
                try:
                    logger.debug(item["attrs"]["id"])
                    if item["attrs"]["id"] is not None:
                        self.markdown_text = "{old}{img_url}\n".format(old=self.markdown_text, img_url=
                        self.post["_embedded"]["contentImages"][int(item["attrs"]["id"])]["url"])
                    self.image_last = self.post["_embedded"]["contentImages"][int(item["attrs"]["id"])]["url"]
                except (IndexError, ValueError):
                    logger.warning("Image {} not found.".format(item["attrs"]["id"]))
                logger.debug(self.markdown_text)
            elif item["type"] == "code_block":
                self.markdown_text += "```\n"
                if "content" in item:
                    self.parse_content(item["content"], item["type"])
                self.markdown_text += "\n```\n"
            elif item["type"] == "bulletList":
                if "content" in item:
                    self.parse_content(item["content"], item["type"])
            elif item["type"] == "orderedList":
                self.item_num = 1
                if "content" in item:
                    self.parse_content(item["content"], item["type"])
            elif item["type"] == "listItem":
                self.parse_content(item["content"], item["type"])

    @staticmethod
    def convert_marks(marks):
        prefix = ""
        suffix = ""
        for mark in marks:
            if mark["type"] == "mention":
                prefix += "["
                suffix = "]({wiki}f/u/{userid}){suffix}".format(wiki=settings["fandom_discussions"]["wiki_url"],
                                                                userid=mark["attrs"]["userId"], suffix=suffix)
            elif mark["type"] == "strong":
                prefix += "**"
                suffix = "**{suffix}".format(suffix=suffix)
            elif mark["type"] == "link":
                prefix += "["
                suffix = "]({link}){suffix}".format(link=mark["attrs"]["href"], suffix=suffix)
            elif mark["type"] == "em":
                prefix += "_"
                suffix = "_" + suffix
        return prefix, suffix


def common_discussions(post: dict, embed: DiscordMessage):
    """A method to setup embeds with common info shared between all types of discussion posts"""
    if settings["fandom_discussions"]["appearance"]["embed"]["show_content"]:
        if post.get("jsonModel") is not None:
            npost = DiscussionsFromHellParser(post)
            embed["description"] = npost.parse()
            if npost.image_last:
                embed["image"]["url"] = npost.image_last
                embed["description"] = embed["description"].replace(npost.image_last, "")
        else:  # Fallback when model is not available
            embed["description"] = post.get("rawContent", "")
    embed["footer"]["text"] = post["forumName"]
    embed["timestamp"] = datetime.datetime.fromtimestamp(post["creationDate"]["epochSecond"],
                                                         tz=datetime.timezone.utc).isoformat()

# discussion/forum - Discussions on the "forum" available via "Discuss" button

@formatter.embed(event="discussion/forum")
def embed_discussion_forum(ctx: Context, post: dict):
    embed = DiscordMessage("embed", "discussion", settings["fandom_discussions"]["webhookURL"])
    common_discussions(post, embed)
    author = _("unknown")  # Fail safe
    if post["createdBy"]["name"]:
        author = post["createdBy"]["name"]
    embed.set_author(author, "{url}f/u/{creatorId}".format(url=settings["fandom_discussions"]["wiki_url"],
                                                           creatorId=post["creatorId"]),
                                                           icon_url=post["createdBy"]["avatarUrl"])
    if not post["isReply"]:
        embed["url"] = "{url}f/p/{threadId}".format(url=settings["fandom_discussions"]["wiki_url"],
                                                    threadId=post["threadId"])
        embed["title"] = _("Created \"{title}\"").format(title=post["title"])
        thread_funnel = post.get("funnel")
        if thread_funnel == "POLL":
            embed.event_type = "discussion/forum/poll"
            embed["title"] = _("Created a poll \"{title}\"").format(title=post["title"])
            if settings["fandom_discussions"]["appearance"]["embed"]["show_content"]:
                poll = post["poll"]
                image_type = False
                if poll["answers"][0]["image"] is not None:
                    image_type = True
                for num, option in enumerate(poll["answers"]):
                    embed.add_field(option["text"] if image_type is True else _("Option {}").format(num + 1),
                                    option["text"] if image_type is False else _(
                                        "__[View image]({image_url})__").format(image_url=option["image"]["url"]),
                                    inline=True)
        elif thread_funnel == "QUIZ":
            embed.event_type = "discussion/forum/quiz"
            embed["title"] = _("Created a quiz \"{title}\"").format(title=post["title"])
            if settings["fandom_discussions"]["appearance"]["embed"]["show_content"]:
                quiz = post["_embedded"]["quizzes"][0]
                embed["description"] = quiz["title"]
                if quiz["image"] is not None:
                    embed["image"]["url"] = quiz["image"]
        elif thread_funnel == "TEXT":
            embed.event_type = "discussion/forum/post"
        else:
            logger.warning(
                "The type of {} is an unknown discussion post type. Please post an issue on the project page to have it added https://gitlab.com/piotrex43/RcGcDw/-/issues.".format(
                    thread_funnel))
            embed.event_type = "unknown"
        if post["_embedded"]["thread"][0]["tags"]:
            tag_displayname = []
            for tag in post["_embedded"]["thread"][0]["tags"]:
                tag_displayname.append("[{title}]({url})".format(title=tag["articleTitle"], url=create_article_path(
                    quote_plus(tag["articleTitle"].replace(" ", "_"), "/:?=&"))))
            if len(", ".join(tag_displayname)) > 1000:
                embed.add_field(formatters_i18n.pgettext("Fandom discussions Tags/Forums", "Tags"), formatters_i18n.pgettext("Fandom discussions amount of Tags/Forums", "{} tags").format(len(post["_embedded"]["thread"][0]["tags"])))
            else:
                embed.add_field(formatters_i18n.pgettext("Fandom discussions Tags/Forums", "Tags"), ", ".join(tag_displayname))
    else:
        embed.event_type = "discussion/forum/reply"
        embed["title"] = _("Replied to \"{title}\"").format(title=post["_embedded"]["thread"][0]["title"])
        embed["url"] = "{url}f/p/{threadId}/r/{postId}".format(url=settings["fandom_discussions"]["wiki_url"],
                                                               threadId=post["threadId"], postId=post["id"])
    return embed


@formatter.compact(event="discussion/forum")
def compact_discussion_forum(ctx: Context, post: dict):
    message = None
    author = _("unknown")  # Fail safe
    if post["createdBy"]["name"]:
        author = post["createdBy"]["name"]
    author_url = "<{url}f/u/{creatorId}>".format(url=settings["fandom_discussions"]["wiki_url"],
                                                 creatorId=post["creatorId"])
    if not post["isReply"]:
        thread_funnel = post.get("funnel")
        msg_text = _("[{author}]({author_url}) created [{title}](<{url}f/p/{threadId}>) in {forumName}")
        if thread_funnel == "POLL":
            event_type = "discussion/forum/poll"
            msg_text = _("[{author}]({author_url}) created a poll [{title}](<{url}f/p/{threadId}>) in {forumName}")
        elif thread_funnel == "QUIZ":
            event_type = "discussion/forum/quiz"
            msg_text = _("[{author}]({author_url}) created a quiz [{title}](<{url}f/p/{threadId}>) in {forumName}")
        elif thread_funnel == "TEXT":
            event_type = "discussion/forum/post"
        else:
            logger.warning(
                "The type of {} is an unknown discussion post type. Please post an issue on the project page to have it added https://gitlab.com/piotrex43/RcGcDw/-/issues.".format(
                    thread_funnel))
            event_type = "unknown"
        message = msg_text.format(author=author, author_url=author_url, title=post["title"],
                                  url=settings["fandom_discussions"]["wiki_url"], threadId=post["threadId"],
                                  forumName=post["forumName"])
    else:
        event_type = "discussion/forum/reply"
        message = _(
            "[{author}]({author_url}) created a [reply](<{url}f/p/{threadId}/r/{postId}>) to [{title}](<{url}f/p/{threadId}>) in {forumName}").format(
            author=author, author_url=author_url, url=settings["fandom_discussions"]["wiki_url"],
            threadId=post["threadId"], postId=post["id"], title=post["_embedded"]["thread"][0]["title"],
            forumName=post["forumName"])
    return DiscordMessage("compact", event_type, ctx.webhook_url, content=message)

# discussion/wall - Wall posts/replies


def compact_author_discussions(post: dict):
    """A common function for a few discussion related foramtters, it's formatting author's name and URL to their profile"""
    author = _("unknown")  # Fail safe
    if post["creatorIp"]:
        author = post["creatorIp"][1:] if settings.get("hide_ips", False) is False else _("Unregistered user")
        author_url = "<{url}wiki/Special:Contributions{creatorIp}>".format(url=settings["fandom_discussions"]["wiki_url"],
                                                                           creatorIp=post["creatorIp"])
    else:
        if post["createdBy"]["name"]:
            author = post["createdBy"]["name"]
            author_url = clean_link(create_article_path("User:{user}".format(user=author)))
        else:
            author_url = "<{url}f/u/{creatorId}>".format(url=settings["fandom_discussions"]["wiki_url"],
                                                     creatorId=post["creatorId"])
    return author, author_url


def embed_author_discussions(post: dict, embed: DiscordMessage):
    author = _("unknown")  # Fail safe
    if post["creatorIp"]:
        author = post["creatorIp"][1:]
        embed.set_author(author if settings.get("hide_ips", False) is False else _("Unregistered user"),
                         "{url}wiki/Special:Contributions{creatorIp}".format(
                             url=settings["fandom_discussions"]["wiki_url"], creatorIp=post["creatorIp"]))
    else:
        if post["createdBy"]["name"]:
            author = post["createdBy"]["name"]
            embed.set_author(author, "{url}wiki/User:{creator}".format(url=settings["fandom_discussions"]["wiki_url"],
                                                                       creator=author.replace(" ", "_")),
                             icon_url=post["createdBy"]["avatarUrl"])
        else:
            embed.set_author(author, "{url}f/u/{creatorId}".format(url=settings["fandom_discussions"]["wiki_url"],
                                                                   creatorId=post["creatorId"]),
                             icon_url=post["createdBy"]["avatarUrl"])


@formatter.embed(event="discussion/wall")
def embed_discussion_wall(ctx: Context, post: dict):
    embed = DiscordMessage("embed", "discussion", settings["fandom_discussions"]["webhookURL"])
    common_discussions(post, embed)
    embed_author_discussions(post, embed)
    user_wall = _("unknown")  # Fail safe
    if post["forumName"].endswith(' Message Wall'):
        user_wall = post["forumName"][:-13]
    if not post["isReply"]:
        embed.event_type = "discussion/wall/post"
        embed["url"] = "{url}wiki/Message_Wall:{user_wall}?threadId={threadId}".format(
            url=settings["fandom_discussions"]["wiki_url"], user_wall=quote_plus(user_wall.replace(" ", "_")),
            threadId=post["threadId"])
        embed["title"] = _("Created \"{title}\" on {user}'s Message Wall").format(title=post["title"], user=user_wall)
    else:
        embed.event_type = "discussion/wall/reply"
        embed["url"] = "{url}wiki/Message_Wall:{user_wall}?threadId={threadId}#{replyId}".format(
            url=settings["fandom_discussions"]["wiki_url"], user_wall=quote_plus(user_wall.replace(" ", "_")),
            threadId=post["threadId"], replyId=post["id"])
        embed["title"] = _("Replied to \"{title}\" on {user}'s Message Wall").format(
            title=post["_embedded"]["thread"][0]["title"], user=user_wall)
    return embed


@formatter.compact(event="discussion/wall")
def compact_discussion_wall(ctx: Context, post: dict):
    author, author_url = compact_author_discussions(post)
    user_wall = _("unknown")  # Fail safe
    if post["forumName"].endswith(' Message Wall'):
        user_wall = post["forumName"][:-13]
    if not post["isReply"]:
        event_type = "discussion/wall/post"
        message = _(
            "[{author}]({author_url}) created [{title}](<{url}wiki/Message_Wall:{user_wall}?threadId={threadId}>) on [{user}'s Message Wall](<{url}wiki/Message_Wall:{user_wall}>)").format(
            author=author, author_url=author_url, title=post["title"], url=settings["fandom_discussions"]["wiki_url"],
            user=user_wall, user_wall=quote_plus(user_wall.replace(" ", "_")), threadId=post["threadId"])
    else:
        event_type = "discussion/wall/reply"
        message = _(
            "[{author}]({author_url}) created a [reply](<{url}wiki/Message_Wall:{user_wall}?threadId={threadId}#{replyId}>) to [{title}](<{url}wiki/Message_Wall:{user_wall}?threadId={threadId}>) on [{user}'s Message Wall](<{url}wiki/Message_Wall:{user_wall}>)").format(
            author=author, author_url=author_url, url=settings["fandom_discussions"]["wiki_url"],
            title=post["_embedded"]["thread"][0]["title"], user=user_wall,
            user_wall=quote_plus(user_wall.replace(" ", "_")), threadId=post["threadId"], replyId=post["id"])
    return DiscordMessage("compact", event_type, ctx.webhook_url, content=message)

# discussion/article_comment - Article comments


@formatter.embed(event="discussion/article_comment")
def embed_discussion_article_comment(ctx: Context, post: dict):
    embed = DiscordMessage("embed", "discussion", settings["fandom_discussions"]["webhookURL"])
    common_discussions(post, embed)
    embed_author_discussions(post, embed)
    article_paths = ctx.comment_page
    if article_paths is None:
        article_paths = {"title": _("unknown"), "fullUrl": settings["fandom_discussions"]["wiki_url"]}  # No page known
    if not post["isReply"]:
        embed.event_type = "discussion/comment/post"
        embed["url"] = "{url}?commentId={commentId}".format(url=article_paths["fullUrl"], commentId=post["threadId"])
        embed["title"] = _("Commented on {article}").format(article=article_paths["title"])
    else:
        embed.event_type = "discussion/comment/reply"
        embed["url"] = "{url}?commentId={commentId}&replyId={replyId}".format(url=article_paths["fullUrl"],
                                                                              commentId=post["threadId"],
                                                                              replyId=post["id"])
        embed["title"] = _("Replied to a comment on {article}").format(article=article_paths["title"])
    embed["footer"]["text"] = article_paths["title"]
    return embed


@formatter.compact(event="discussion/article_comment")
def compact_discussion_article_comment(ctx: Context, post: dict):
    author, author_url = compact_author_discussions(post)
    article_paths = ctx.comment_page
    if article_paths is None:
        article_paths = {"title": _("unknown"), "fullUrl": settings["fandom_discussions"]["wiki_url"]}  # No page known
    article_paths["fullUrl"] = article_paths["fullUrl"].replace(")", "\)").replace("()", "\(")
    if not post["isReply"]:
        event_type = "discussion/comment/post"
        message = _(
            "[{author}]({author_url}) created a [comment](<{url}?commentId={commentId}>) on [{article}](<{url}>)").format(
            author=author, author_url=author_url, url=article_paths["fullUrl"], article=article_paths["title"],
            commentId=post["threadId"])
    else:
        event_type = "discussion/comment/reply"
        message = _(
            "[{author}]({author_url}) created a [reply](<{url}?commentId={commentId}&replyId={replyId}>) to a [comment](<{url}?commentId={commentId}>) on [{article}](<{url}>)").format(
            author=author, author_url=author_url, url=article_paths["fullUrl"], article=article_paths["title"],
            commentId=post["threadId"], replyId=post["id"])
    return DiscordMessage("compact", event_type, ctx.webhook_url, content=message)
