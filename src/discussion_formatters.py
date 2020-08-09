import datetime, logging
import json
import gettext
from urllib.parse import quote_plus

from src.configloader import settings
from src.misc import DiscordMessage, send_to_discord, escape_formatting
from src.i18n import discussion_formatters

_ = discussion_formatters.gettext


discussion_logger = logging.getLogger("rcgcdw.discussion_formatter")


def compact_formatter(post_type, post):
	"""Compact formatter for Fandom discussions."""
	message = None
	if post_type == "FORUM":
		author = post["createdBy"]["name"]
		author_url = "<{url}f/u/{creatorId}>".format(url=settings["fandom_discussions"]["wiki_url"], creatorId=post["creatorId"])
	elif post["creatorIp"]:
		author = post["creatorIp"][1:]
		author_url = "<{url}wiki/Special:Contributions{creatorIp}>".format(url=settings["fandom_discussions"]["wiki_url"], creatorIp=post["creatorIp"])
	else:
		author = post["createdBy"]["name"]
		author_url = "<{url}wiki/User:{author}>".format(url=settings["fandom_discussions"]["wiki_url"], author=author)
	if post_type == "FORUM":
		if not post["isReply"]:
			thread_funnel = post.get("funnel")
			msg_text = "[{author}]({author_url}) created [{title}](<{url}f/p/{threadId}>) in {forumName}"
			if thread_funnel == "POLL":
				msg_text = "[{author}]({author_url}) created a poll [{title}](<{url}f/p/{threadId}>) in {forumName}"
			elif thread_funnel == "QUIZ":
				msg_text = "[{author}]({author_url}) created a quiz [{title}](<{url}f/p/{threadId}>) in {forumName}"
			elif thread_funnel != "TEXT":
				discussion_logger.warning("The type of {} is an unknown discussion post type. Please post an issue on the project page to have it added https://gitlab.com/piotrex43/RcGcDw/-/issues.".format(thread_funnel))
			message = _(msg_text).format(author=author, author_url=author_url, title=post["title"], url=settings["fandom_discussions"]["wiki_url"], threadId=post["threadId"], forumName=post["forumName"])
		else:
			message = _("[{author}]({author_url}) created a [reply](<{url}f/p/{threadId}/r/{postId}>) to [{title}](<{url}f/p/{threadId}>) in {forumName}").format(author=author, author_url=author_url, url=settings["fandom_discussions"]["wiki_url"], threadId=post["threadId"], postId=post["id"], title=post["_embedded"]["thread"][0]["title"], forumName=post["forumName"])
	elif post_type == "WALL":
		user_wall = _("unknown")  # Fail safe
		if post["forumName"].endswith(' Message Wall'):
			user_wall = post["forumName"][:-13]
		if not post["isReply"]:
			message = _("[{author}]({author_url}) created [{title}](<{url}wiki/Message_Wall:{user_wall}?threadId={threadId}>) on [{user}'s Message Wall](<{url}wiki/Message_Wall:{user_wall}>)").format(author=author, author_url=author_url, title=post["title"], url=settings["fandom_discussions"]["wiki_url"], user=user_wall, user_wall=quote_plus(user_wall.replace(" ", "_")), threadId=post["threadId"])
		else:
			message = _("[{author}]({author_url}) created a [reply](<{url}wiki/Message_Wall:{user_wall}?threadId={threadId}#{replyId}>) to [{title}](<{url}wiki/Message_Wall:{user_wall}?threadId={threadId}>) on [{user}'s Message Wall](<{url}wiki/Message_Wall:{user_wall}>)").format(author=author, author_url=author_url, url=settings["fandom_discussions"]["wiki_url"], title=post["_embedded"]["thread"][0]["title"], user=user_wall, user_wall=quote_plus(user_wall.replace(" ", "_")), threadId=post["threadId"], replyId=post["id"])
	elif post_type == "ARTICLE_COMMENT":
		discussion_logger.warning("Article comments are not yet implemented. For reasons see https://gitlab.com/piotrex43/RcGcDw/-/issues/126#note_366480037")
		article_page = _("unknown")  # No page known
		if not post["isReply"]:
			message = _("[{author}]({author_url}) created a [comment](<{url}wiki/{article}?commentId={commentId}>) on [{article}](<{url}wiki/{article}>)").format(author=author, author_url=author_url, url=settings["fandom_discussions"]["wiki_url"], article=article_page, commentId=post["threadId"])
		else:
			message = _("[{author}]({author_url}) created a [reply](<{url}wiki/{article}?threadId={threadId}) to a [comment](<{url}wiki/{article}?commentId={commentId}&replyId={replyId}>) on [{article}](<{url}wiki/{article}>)").format(author=author, author_url=author_url, url=settings["fandom_discussions"]["wiki_url"], article=article_page, commentId=post["threadId"], replyId=post["id"])
	else:
		discussion_logger.warning("The type of {} is an unknown discussion post type. Please post an issue on the project page to have it added https://gitlab.com/piotrex43/RcGcDw/-/issues.".format(post_type))
	send_to_discord(DiscordMessage("compact", "discussion", settings["fandom_discussions"]["webhookURL"], content=message))


def embed_formatter(post_type, post):
	"""Embed formatter for Fandom discussions."""
	embed = DiscordMessage("embed", "discussion", settings["fandom_discussions"]["webhookURL"])
	if post_type == "FORUM":
		embed.set_author(post["createdBy"]["name"], "{url}f/u/{creatorId}".format(url=settings["fandom_discussions"]["wiki_url"], creatorId=post["creatorId"]), icon_url=post["createdBy"]["avatarUrl"])
	elif post["creatorIp"]:
		embed.set_author(post["creatorIp"][1:], "{url}wiki/Special:Contributions{creatorIp}".format(url=settings["fandom_discussions"]["wiki_url"], creatorIp=post["creatorIp"]))
	else:
		embed.set_author(post["createdBy"]["name"], "{url}wiki/User:{creator}".format(url=settings["fandom_discussions"]["wiki_url"], creator=post["createdBy"]["name"]), icon_url=post["createdBy"]["avatarUrl"])
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
	embed["timestamp"] = datetime.datetime.fromtimestamp(post["creationDate"]["epochSecond"], tz=datetime.timezone.utc).isoformat()
	if post_type == "FORUM":
		if not post["isReply"]:
			embed["url"] = "{url}f/p/{threadId}".format(url=settings["fandom_discussions"]["wiki_url"], threadId=post["threadId"])
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
						embed.add_field(option["text"] if image_type is True else _("Option {}").format(num+1),
										option["text"] if image_type is False else _("__[View image]({image_url})__").format(image_url=option["image"]["url"]),
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
				discussion_logger.warning("The type of {} is an unknown discussion post type. Please post an issue on the project page to have it added https://gitlab.com/piotrex43/RcGcDw/-/issues.".format(thread_funnel))
		else:
			embed.event_type = "discussion/forum/reply"
			embed["title"] = _("Replied to \"{title}\"").format(title=post["_embedded"]["thread"][0]["title"])
			embed["url"] = "{url}f/p/{threadId}/r/{postId}".format(url=settings["fandom_discussions"]["wiki_url"], threadId=post["threadId"], postId=post["id"])
	elif post_type == "WALL":
		user_wall = _("unknown")  # Fail safe
		if post["forumName"].endswith(' Message Wall'):
			user_wall = post["forumName"][:-13]
		if not post["isReply"]:
			embed.event_type = "discussion/wall/post"
			embed["url"] = "{url}wiki/Message_Wall:{user_wall}?threadId={threadId}".format(url=settings["fandom_discussions"]["wiki_url"], user_wall=quote_plus(user_wall.replace(" ", "_")), threadId=post["threadId"])
			embed["title"] = _("Created \"{title}\" on {user}'s Message Wall").format(title=post["title"], user=user_wall)
		else:
			embed.event_type = "discussion/wall/reply"
			embed["url"] = "{url}wiki/Message_Wall:{user_wall}?threadId={threadId}#{replyId}".format(url=settings["fandom_discussions"]["wiki_url"], user_wall=quote_plus(user_wall.replace(" ", "_")), threadId=post["threadId"], replyId=post["id"])
			embed["title"] = _("Replied to \"{title}\" on {user}'s Message Wall").format(title=post["_embedded"]["thread"][0]["title"], user=user_wall)
	elif post_type == "ARTICLE_COMMENT":
		discussion_logger.warning("Article comments are not yet implemented. For reasons see https://gitlab.com/piotrex43/RcGcDw/-/issues/126#note_366480037")
		article_page = _("unknown")  # No page known
		if not post["isReply"]:
			embed.event_type = "discussion/comment/post"
			# embed["url"] = "{url}wiki/{article}?commentId={commentId}".format(url=settings["fandom_discussions"]["wiki_url"], article=quote_plus(article_page.replace(" ", "_")), commentId=post["threadId"])
			embed["title"] = _("Commented on {article}").format(article=article_page)
		else:
			embed.event_type = "discussion/comment/reply"
			# embed["url"] = "{url}wiki/{article}?commentId={commentId}&replyId={replyId}".format(url=settings["fandom_discussions"]["wiki_url"], article=quote_plus(article_page.replace(" ", "_")), commentId=post["threadId"], replyId=post["id"])
			embed["title"] = _("Replied to a comment on {article}").format(article=article_page)
		embed["footer"]["text"] = article_page
	else:
		discussion_logger.warning("The type of {} is an unknown discussion post type. Please post an issue on the project page to have it added https://gitlab.com/piotrex43/RcGcDw/-/issues.".format(post_type))
	embed.finish_embed()
	send_to_discord(embed)


class DiscussionsFromHellParser:
	"""This class converts fairly convoluted Fandom jsonModal of a discussion post into Markdown formatted usable thing. Takes string, returns string.
		Kudos to MarkusRost for allowing me to implement this formatter based on his code in Wiki-Bot."""
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
					self.markdown_text = "{old}{pre}{text}{suf}".format(old=self.markdown_text, pre=prefix, text=escape_formatting(item["text"]), suf=suffix)
				else:
					if ctype == "code_block":
						self.markdown_text += item["text"]  # ignore formatting on preformatted text which cannot have additional formatting anyways
					else:
						self.markdown_text += escape_formatting(item["text"])
			elif item["type"] == "paragraph":
				if "content" in item:
					self.parse_content(item["content"], item["type"])
				self.markdown_text += "\n"
			elif item["type"] == "openGraph":
				if not item["attrs"]["wasAddedWithInlineLink"]:
					self.markdown_text = "{old}{link}\n".format(old=self.markdown_text, link=item["attrs"]["url"])
			elif item["type"] == "image":
				try:
					discussion_logger.debug(item["attrs"]["id"])
					if item["attrs"]["id"] is not None:
						self.markdown_text = "{old}{img_url}\n".format(old=self.markdown_text, img_url=self.post["_embedded"]["contentImages"][int(item["attrs"]["id"])]["url"])
					self.image_last = self.post["_embedded"]["contentImages"][int(item["attrs"]["id"])]["url"]
				except (IndexError, ValueError):
					discussion_logger.warning("Image {} not found.".format(item["attrs"]["id"]))
				discussion_logger.debug(self.markdown_text)
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

	def convert_marks(self, marks):
		prefix = ""
		suffix = ""
		for mark in marks:
			if mark["type"] == "mention":
				prefix += "["
				suffix = "]({wiki}f/u/{userid}){suffix}".format(wiki=settings["fandom_discussions"]["wiki_url"], userid=mark["attrs"]["userId"], suffix=suffix)
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