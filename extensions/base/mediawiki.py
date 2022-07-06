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
import ipaddress
import logging
import math
import re
import time
import datetime
from collections import OrderedDict
from src.discord.message import DiscordMessage
from src.api import formatter
from src.i18n import formatters_i18n
from src.api.context import Context
from src.api.util import embed_helper, sanitize_to_url, parse_mediawiki_changes, clean_link, compact_author, \
    create_article_path, sanitize_to_markdown, compact_summary
from src.configloader import settings
from src.exceptions import *

_ = formatters_i18n.gettext
ngettext = formatters_i18n.ngettext

logger = logging.getLogger("extensions.base")

if 1 == 2:  # additional translation strings in unreachable code
    print(_("director"), _("bot"), _("editor"), _("directors"), _("sysop"), _("bureaucrat"), _("reviewer"),
          _("autoreview"), _("autopatrol"), _("wiki_guardian"))


# Page edit - event edit, New - page creation


@formatter.embed(event="edit", mode="embed", aliases=["new"])
def embed_edit(ctx: Context, change: dict) -> DiscordMessage:
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    action = ctx.event
    editsize = change["newlen"] - change["oldlen"]
    if editsize > 0:
        embed["color"] = min(65280, 35840 + (math.floor(editsize / 52)) * 256)  # Choose shade of green
    elif editsize < 0:
        embed["color"] = min(16711680, 9175040 + (math.floor(abs(editsize) / 52)) * 65536)  # Choose shade of red
    elif editsize == 0:
        embed["color"] = 8750469
    if change["title"].startswith("MediaWiki:Tag-"):  # Refresh tag list when tag display name is edited
        ctx.client.refresh_internal_data()
    # Sparse is better than dense.
    # Readability counts.
    embed["url"] = "{wiki}index.php?title={article}&curid={pageid}&diff={diff}&oldid={oldrev}".format(
        wiki=ctx.client.WIKI_SCRIPT_PATH,
        pageid=change["pageid"],
        diff=change["revid"],
        oldrev=change["old_revid"],
        article=sanitize_to_url(change["title"])
    )
    embed["title"] = "{redirect}{article} ({new}{minor}{bot}{space}{editsize})".format(
        redirect="⤷ " if "redirect" in change else "",
        article=sanitize_to_markdown(change["title"]),
        editsize="+" + str(editsize) if editsize > 0 else editsize,
        new=_("(N!) ") if action == "new" else "",
        minor=_("m") if action == "edit" and "minor" in change else "",
        bot=_('b') if "bot" in change else "",
        space=" " if "bot" in change or (action == "edit" and "minor" in change) or action == "new" else "")
    if settings["appearance"]["embed"]["show_edit_changes"]:
        try:
            if action == "new":
                changed_content = ctx.client.make_api_request(
                    "?action=compare&format=json&fromslots=main&torev={diff}&fromtext-main=&topst=1&prop=diff".format(
                        diff=change["revid"]), "compare", "*")
            else:
                changed_content = ctx.client.make_api_request(
                    "?action=compare&format=json&fromrev={oldrev}&torev={diff}&topst=1&prop=diff".format(
                        diff=change["revid"], oldrev=change["old_revid"]), "compare", "*")
        except (ServerError, MediaWikiError):
            changed_content = None
        if changed_content:
            parse_mediawiki_changes(ctx, changed_content, embed)
        else:
            logger.warning("Unable to download data on the edit content!")
    embed_helper(ctx, embed, change)
    return embed


@formatter.compact(event="edit", mode="compact", aliases=["new"])
def compact_edit(ctx: Context, change: dict) -> DiscordMessage:
    parsed_comment = compact_summary(ctx)
    author, author_url = compact_author(ctx, change)
    action = ctx.event
    edit_link = clean_link("{wiki}index.php?title={article}&curid={pageid}&diff={diff}&oldid={oldrev}".format(
        wiki=ctx.client.WIKI_SCRIPT_PATH, pageid=change["pageid"], diff=change["revid"], oldrev=change["old_revid"],
        article=sanitize_to_url(change["title"])))
    logger.debug(edit_link)
    edit_size = change["newlen"] - change["oldlen"]
    sign = ""
    if edit_size > 0:
        sign = "+"
    bold = ""
    if abs(edit_size) > 500:
        bold = "**"
    if action == "edit":
        content = _(
            "[{author}]({author_url}) edited [{article}]({edit_link}){comment} {bold}({sign}{edit_size}){bold}").format(
            author=author, author_url=author_url, article=sanitize_to_markdown(change["title"]), edit_link=edit_link, comment=parsed_comment,
            edit_size=edit_size, sign=sign, bold=bold)
    else:
        content = _(
            "[{author}]({author_url}) created [{article}]({edit_link}){comment} {bold}({sign}{edit_size}){bold}").format(
            author=author, author_url=author_url, article=sanitize_to_markdown(change["title"]), edit_link=edit_link, comment=parsed_comment,
            edit_size=edit_size, sign=sign, bold=bold)
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)


# Upload - upload/reupload, upload/upload
@formatter.embed(event="upload/upload", mode="embed", aliases=["upload/overwrite", "upload/revert"])
def embed_upload_upload(ctx, change) -> DiscordMessage:
    license = None
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    action = ctx.event
    # Requesting more information on the image
    request_for_image_data = None
    try:
        params = OrderedDict()
        params["action"] = "query"
        params["format"] = "json"
        if settings["license_detection"] and action == "upload/upload":
            params["prop"] = "imageinfo|revisions"
            params["rvprop"] = "content"
            params["rvslots"] = "main"
        else:
            params["prop"] = "imageinfo"
        params["titles"] = change["title"]
        params["iiprop"] = "timestamp|url|archivename"
        params["iilimit"] = "5"
        request_for_image_data = ctx.client.make_api_request(params, "query", "pages")
    except (ServerError, MediaWikiError):
        logger.exception(
            "Couldn't retrieve more information about the image {} because of server/MediaWiki error".format(
                change["title"]))
    except (ClientError, BadRequest):
        raise
    except KeyError:
        logger.exception(
            "Couldn't retrieve more information about the image {} because of unknown error".format(
                change["title"]))
    else:
        if "-1" not in request_for_image_data:  # Image still exists and not removed
            image_data = next(iter(request_for_image_data.values()))
        else:
            logger.warning("Request for additional image information have failed. The preview will not be shown.")
            request_for_image_data = None
    embed["url"] = create_article_path(sanitize_to_url(change["title"]))
    image_direct_url = None
    # Make a request for file revisions so we can get direct URL to the image for embed
    if request_for_image_data is not None:
        try:
            urls = image_data["imageinfo"]
            for num, revision in enumerate(urls):
                if revision["timestamp"] == change["logparams"][
                    "img_timestamp"]:  # find the correct revision corresponding for this log entry
                    image_direct_url = "{rev}?{cache}".format(rev=revision["url"],
                                                              cache=int(time.time() * 5))  # cachebusting
                    break
        except KeyError:
            logger.exception(
                "Wiki did not respond with extended information about file. The preview will not be shown.")
    else:
        logger.warning("Request for additional image information have failed. The preview will not be shown.")
    if action in ("upload/overwrite", "upload/revert"):
        if image_direct_url:
            try:
                revision = image_data["imageinfo"][num + 1]
            except IndexError:
                logger.exception(
                    "Could not analize the information about the image (does it have only one version when expected more in overwrite?) which resulted in no Options field: {}".format(
                        image_data["imageinfo"]))
            else:
                undolink = "{wiki}index.php?title={filename}&action=revert&oldimage={archiveid}".format(
                    wiki=ctx.client.WIKI_SCRIPT_PATH, filename=sanitize_to_url(change["title"]),
                    archiveid=revision["archivename"])
                embed.add_field(_("Options"), _("([preview]({link}) | [undo]({undolink}))").format(
                    link=image_direct_url, undolink=undolink))
            if settings["appearance"]["embed"]["embed_images"]:
                embed["image"]["url"] = image_direct_url
        if action == "upload/overwrite":
            embed["title"] = _("Uploaded a new version of {name}").format(name=sanitize_to_markdown(change["title"]))
        elif action == "upload/revert":
            embed["title"] = _("Reverted a version of {name}").format(name=sanitize_to_markdown(change["title"]))
    else:
        embed["title"] = _("Uploaded {name}").format(name=sanitize_to_markdown(change["title"]))
        if settings["license_detection"] and image_direct_url:
            try:
                content = image_data['revisions'][0]["slots"]["main"]['*']
                matches = re.search(re.compile(settings["license_regex"], re.IGNORECASE), content)
                if matches is not None:
                    license = matches.group("license")
                else:
                    if re.search(re.compile(settings["license_regex_detect"], re.IGNORECASE), content) is None:
                        license = _("**No license!**")
                    else:
                        license = "?"
            except IndexError:
                logger.error(
                    "Given regex for the license detection is incorrect. It does not have a capturing group called \"license\" specified. Please fix license_regex value in the config!")
                license = "?"
            except re.error:
                logger.error(
                    "Given regex for the license detection is incorrect. Please fix license_regex or license_regex_detect values in the config!")
                license = "?"
            except KeyError:
                logger.exception(
                    "Unknown error when retriefing the image data for a license, full content: {}".format(image_data))
        if image_direct_url:
            embed.add_field(_("Options"), _("([preview]({link}))").format(link=image_direct_url))
            if settings["appearance"]["embed"]["embed_images"]:
                embed["image"]["url"] = image_direct_url
    embed_helper(ctx, embed, change)
    if license is not None:
        embed["description"] += _("\nLicense: {}").format(license)
    return embed


@formatter.compact(event="upload/revert", mode="compact")
def compact_upload_revert(ctx, change) -> DiscordMessage:
    author, author_url = compact_author(ctx, change)
    file_link = clean_link(create_article_path(sanitize_to_url(change["title"])))
    parsed_comment = compact_summary(ctx)
    content = _("[{author}]({author_url}) reverted a version of [{file}]({file_link}){comment}").format(
        author=author, author_url=author_url, file=sanitize_to_markdown(change["title"]), file_link=file_link,
        comment=parsed_comment)
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)


@formatter.compact(event="upload/overwrite", mode="compact")
def compact_upload_overwrite(ctx, change) -> DiscordMessage:
    author, author_url = compact_author(ctx, change)
    file_link = clean_link(create_article_path(sanitize_to_url(change["title"])))
    parsed_comment = compact_summary(ctx)
    content = _("[{author}]({author_url}) uploaded a new version of [{file}]({file_link}){comment}").format(
        author=author, author_url=author_url, file=sanitize_to_markdown(change["title"]), file_link=file_link,
        comment=parsed_comment)
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)


@formatter.compact(event="upload/upload", mode="compact")
def compact_upload_upload(ctx, change) -> DiscordMessage:
    author, author_url = compact_author(ctx, change)
    file_link = clean_link(create_article_path(sanitize_to_url(change["title"])))
    parsed_comment = compact_summary(ctx)
    content = _("[{author}]({author_url}) uploaded [{file}]({file_link}){comment}").format(author=author,
                                                                                           author_url=author_url,
                                                                                           file=sanitize_to_markdown(
                                                                                               change["title"]),
                                                                                           file_link=file_link,
                                                                                           comment=parsed_comment)
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)


# delete/delete - Page deletion
@formatter.embed(event="delete/delete", mode="embed")
def embed_delete_delete(ctx, change) -> DiscordMessage:
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change)
    embed['url'] = create_article_path(sanitize_to_url(change["title"]))
    embed["title"] = _("Deleted page {article}").format(article=sanitize_to_markdown(change["title"]))
    return embed


@formatter.compact(event="delete/delete", mode="compact")
def compact_delete_delete(ctx, change) -> DiscordMessage:
    parsed_comment = compact_summary(ctx)
    author, author_url = compact_author(ctx, change)
    page_link = clean_link(create_article_path(sanitize_to_url(change["title"])))
    content = _("[{author}]({author_url}) deleted [{page}]({page_link}){comment}").format(author=author,
                                                                                          author_url=author_url,
                                                                                          page=sanitize_to_markdown(
                                                                                              change["title"]),
                                                                                          page_link=page_link,
                                                                                          comment=parsed_comment)
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)


# delete/delete_redir - Redirect deletion
@formatter.embed(event="delete/delete_redir", mode="embed")
def embed_delete_delete_redir(ctx, change) -> DiscordMessage:
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change)
    embed['url'] = create_article_path(sanitize_to_url(change["title"]))
    embed["title"] = _("Deleted redirect {article} by overwriting").format(
        article=sanitize_to_markdown(change["title"]))
    return embed


@formatter.compact(event="delete/delete_redir", mode="compact")
def compact_delete_delete_redir(ctx, change) -> DiscordMessage:
    page_link = clean_link(create_article_path(sanitize_to_url(change["title"])))
    author, author_url = compact_author(ctx, change)
    parsed_comment = compact_summary(ctx)
    content = _("[{author}]({author_url}) deleted redirect by overwriting [{page}]({page_link}){comment}").format(
        author=author, author_url=author_url, page=sanitize_to_markdown(change["title"]), page_link=page_link,
        comment=parsed_comment)
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)


# delete/restore - Restoring a page


@formatter.embed(event="delete/restore", mode="embed")
def embed_delete_restore(ctx, change) -> DiscordMessage:
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change)
    embed['url'] = create_article_path(sanitize_to_url(change["title"]))
    embed["title"] = _("Restored {article}").format(article=sanitize_to_markdown(change["title"]))
    return embed


@formatter.compact(event="delete/restore", mode="compact")
def compact_delete_restore(ctx, change) -> DiscordMessage:
    page_link = clean_link(create_article_path(sanitize_to_url(change["title"])))
    author, author_url = compact_author(ctx, change)
    parsed_comment = compact_summary(ctx)
    content = _("[{author}]({author_url}) restored [{article}]({article_url}){comment}").format(author=author,
                                                                                                author_url=author_url,
                                                                                                article=sanitize_to_markdown(
                                                                                                    change["title"]),
                                                                                                article_url=page_link,
                                                                                                comment=parsed_comment)
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)


# delete/event - Deleting an event with revdelete feature


@formatter.embed(event="delete/event", mode="embed")
def embed_delete_event(ctx, change) -> DiscordMessage:
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change)
    embed['url'] = create_article_path("Special:RecentChanges")
    embed["title"] = _("Changed visibility of log events")
    return embed


@formatter.compact(event="delete/event", mode="compact")
def compact_delete_event(ctx, change) -> DiscordMessage:
    author, author_url = compact_author(ctx, change)
    parsed_comment = compact_summary(ctx)
    content = _("[{author}]({author_url}) changed visibility of log events{comment}").format(author=author,
                                                                                             author_url=author_url,
                                                                                             comment=parsed_comment)
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)


# delete/revision - Deleting revision information

@formatter.embed(event="delete/revision", mode="embed")
def embed_delete_revision(ctx, change) -> DiscordMessage:
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change)
    amount = len(change["logparams"]["ids"])
    embed['url'] = create_article_path(sanitize_to_url(change["title"]))
    embed["title"] = ngettext("Changed visibility of revision on page {article} ",
                              "Changed visibility of {amount} revisions on page {article} ", amount).format(
        article=sanitize_to_markdown(change["title"]), amount=amount)
    return embed


@formatter.compact(event="delete/revision", mode="compact")
def compact_delete_revision(ctx, change) -> DiscordMessage:
    author, author_url = compact_author(ctx, change)
    amount = len(change["logparams"]["ids"])
    link = clean_link(create_article_path(sanitize_to_url(change["title"])))
    parsed_comment = compact_summary(ctx)
    content = ngettext(
        "[{author}]({author_url}) changed visibility of revision on page [{article}]({article_url}){comment}",
        "[{author}]({author_url}) changed visibility of {amount} revisions on page [{article}]({article_url}){comment}",
        amount).format(author=author, author_url=author_url,
                       article=sanitize_to_markdown(change["title"]), article_url=link, amount=amount, comment=parsed_comment)
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)


# move/move - Moving pages


@formatter.embed(event="move/move", mode="embed")
def embed_move_move(ctx, change) -> DiscordMessage:
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change, set_desc=False)
    embed["url"] = create_article_path(sanitize_to_url(change["logparams"]['target_title']))
    embed["description"] = "{supress}. {desc}".format(desc=ctx.parsedcomment,
                                                      supress=_("No redirect has been made") if "suppressredirect" in
                                                              change["logparams"] else _("A redirect has been made"))
    embed["title"] = _("Moved {redirect}{article} to {target}").format(redirect="⤷ " if "redirect" in change else "",
                                                                       article=sanitize_to_markdown(change["title"]),
                                                                       target=sanitize_to_markdown(
                                                                           change["logparams"]['target_title']))
    return embed


@formatter.compact(event="move/move", mode="compact")
def compact_move_move(ctx, change) -> DiscordMessage:
    author, author_url = compact_author(ctx, change)
    link = clean_link(create_article_path(sanitize_to_url(change["logparams"]['target_title'])))
    redirect_status = _("without making a redirect") if "suppressredirect" in change["logparams"] else _(
        "with a redirect")
    parsed_comment = compact_summary(ctx)
    content = _(
        "[{author}]({author_url}) moved {redirect}*{article}* to [{target}]({target_url}) {made_a_redirect}{comment}").format(
        author=author, author_url=author_url, redirect="⤷ " if "redirect" in change else "", article=sanitize_to_markdown(change["title"]),
        target=sanitize_to_markdown(change["logparams"]['target_title']), target_url=link, comment=parsed_comment,
        made_a_redirect=redirect_status)
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)


# move/move_redir - Move over redirect


@formatter.embed(event="move/move_redir", mode="embed")
def embed_move_move_redir(ctx, change) -> DiscordMessage:
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change, set_desc=False)
    embed["url"] = create_article_path(sanitize_to_url(change["logparams"]['target_title']))
    embed["description"] = "{supress}. {desc}".format(desc=ctx.parsedcomment,
                                                      supress=_("No redirect has been made") if "suppressredirect" in
                                                              change["logparams"] else _("A redirect has been made"))
    embed["title"] = _("Moved {redirect}{article} to {title} over redirect").format(
        redirect="⤷ " if "redirect" in change else "", article=sanitize_to_markdown(change["title"]),
        title=sanitize_to_markdown(change["logparams"]["target_title"]))
    return embed


@formatter.compact(event="move/move_redir", mode="compact")
def compact_move_move_redir(ctx, change) -> DiscordMessage:
    author, author_url = compact_author(ctx, change)
    link = clean_link(create_article_path(sanitize_to_url(change["logparams"]['target_title'])))
    redirect_status = _("without making a redirect") if "suppressredirect" in change["logparams"] else _(
        "with a redirect")
    parsed_comment = compact_summary(ctx)
    content = _(
        "[{author}]({author_url}) moved {redirect}*{article}* over redirect to [{target}]({target_url}) {made_a_redirect}{comment}").format(
        author=author, author_url=author_url, redirect="⤷ " if "redirect" in change else "",
        article=sanitize_to_markdown(change["title"]),
        target=sanitize_to_markdown(change["logparams"]['target_title']), target_url=link, comment=parsed_comment,
        made_a_redirect=redirect_status)
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)


# protect/move_prot - Moving protection


@formatter.embed(event="protect/move_prot", mode="embed")
def embed_protect_move_prot(ctx, change):
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change)
    embed["url"] = create_article_path(sanitize_to_url(change["logparams"]["oldtitle_title"]))
    embed["title"] = _("Moved protection settings from {redirect}{article} to {title}").format(
        redirect="⤷ " if "redirect" in change else "",
        article=sanitize_to_markdown(change["logparams"]["oldtitle_title"]),
        title=sanitize_to_markdown(change["title"]))
    return embed


@formatter.compact(event="protect/move_prot", mode="compact")
def compact_protect_move_prot(ctx, change):
    author, author_url = compact_author(ctx, change)
    link = clean_link(create_article_path(sanitize_to_url(change["logparams"]["oldtitle_title"])))
    parsed_comment = compact_summary(ctx)
    content = _(
        "[{author}]({author_url}) moved protection settings from {redirect}*{article}* to [{target}]({target_url}){comment}").format(
        author=author, author_url=author_url, redirect="⤷ " if "redirect" in change else "",
        article=sanitize_to_markdown(change["logparams"]["oldtitle_title"]),
        target=sanitize_to_markdown(change["title"]), target_url=link, comment=parsed_comment)
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)


# protect/protect - Creating protection


@formatter.embed(event="protect/protect", mode="embed")
def embed_protect_protect(ctx, change):
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change, set_desc=False)
    embed["url"] = create_article_path(sanitize_to_url(change["title"]))
    embed["title"] = _("Protected {target}").format(target=sanitize_to_markdown(change["title"]))
    embed["description"] = "{settings}{cascade} | {reason}".format(
        settings=sanitize_to_markdown(change["logparams"].get("description", "")),
        cascade=_(" [cascading]") if "cascade" in change["logparams"] else "",
        reason=ctx.parsedcomment)
    return embed


@formatter.compact(event="protect/protect", mode="compact")
def compact_protect_protect(ctx, change):
    author, author_url = compact_author(ctx, change)
    link = clean_link(create_article_path(sanitize_to_url(change["title"])))
    parsed_comment = compact_summary(ctx)
    content = _(
        "[{author}]({author_url}) protected [{article}]({article_url}) with the following settings: {settings}{comment}").format(
        author=author, author_url=author_url,
        article=sanitize_to_markdown(change["title"]), article_url=link,
        settings=change["logparams"].get("description", "") + (
            _(" [cascading]") if "cascade" in change["logparams"] else ""),
        comment=parsed_comment)
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)


# protect/modify - Changing protection settings


@formatter.embed(event="protect/modify", mode="embed")
def embed_protect_modify(ctx, change):
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change, set_desc=False)
    embed["url"] = create_article_path(sanitize_to_url(change["title"]))
    embed["title"] = _("Changed protection level for {article}").format(article=sanitize_to_markdown(change["title"]))
    embed["description"] = "{settings}{cascade} | {reason}".format(
        settings=sanitize_to_markdown(change["logparams"].get("description", "")),
        cascade=_(" [cascading]") if "cascade" in change["logparams"] else "",
        reason=ctx.parsedcomment)
    return embed


@formatter.compact(event="protect/modify", mode="compact")
def compact_protect_modify(ctx, change):
    author, author_url = compact_author(ctx, change)
    link = clean_link(create_article_path(sanitize_to_url(change["title"])))
    parsed_comment = compact_summary(ctx)
    content = _(
        "[{author}]({author_url}) modified protection settings of [{article}]({article_url}) to: {settings}{comment}").format(
        author=author, author_url=author_url,
        article=sanitize_to_markdown(change["title"]), article_url=link,
        settings=sanitize_to_markdown(change["logparams"].get("description", "")) + (
            _(" [cascading]") if "cascade" in change["logparams"] else ""),
        comment=parsed_comment)
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)


# protect/unprotect - Unprotecting a page


@formatter.embed(event="protect/unprotect", mode="embed")
def embed_protect_unprotect(ctx, change):
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change)
    embed["url"] = create_article_path(sanitize_to_url(change["title"]))
    embed["title"] = _("Removed protection from {article}").format(article=sanitize_to_markdown(change["title"]))
    return embed


@formatter.compact(event="protect/unprotect", mode="compact")
def compact_protect_unprotect(ctx, change):
    author, author_url = compact_author(ctx, change)
    link = clean_link(create_article_path(sanitize_to_url(change["title"])))
    parsed_comment = compact_summary(ctx)
    content = _("[{author}]({author_url}) removed protection from [{article}]({article_url}){comment}").format(
        author=author, author_url=author_url, article=sanitize_to_markdown(change["title"]), article_url=link,
        comment=parsed_comment)
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)


# block/block - Blocking an user
def block_expiry(change: dict) -> str:
    if change["logparams"]["duration"] in ["infinite", "indefinite", "infinity", "never"]:
        return _("for infinity and beyond")
    else:
        if "expiry" in change["logparams"]:
            expiry_date_time_obj = datetime.datetime.strptime(change["logparams"]["expiry"], '%Y-%m-%dT%H:%M:%SZ')
            timestamp_date_time_obj = datetime.datetime.strptime(change["timestamp"], '%Y-%m-%dT%H:%M:%SZ')
            timedelta_for_expiry = (expiry_date_time_obj - timestamp_date_time_obj).total_seconds()
            years, days, hours, minutes = timedelta_for_expiry // 31557600, timedelta_for_expiry % 31557600 // 86400, \
                                          timedelta_for_expiry % 86400 // 3600, timedelta_for_expiry % 3600 // 60
            if not any([years, days, hours, minutes]):
                return _("for less than a minute")
            time_names = (
                ngettext("year", "years", years), ngettext("day", "days", days), ngettext("hour", "hours", hours),
                ngettext("minute", "minutes", minutes))
            final_time = []
            for num, timev in enumerate([years, days, hours, minutes]):
                if timev:
                    final_time.append(
                        _("for {time_number} {time_unit}").format(time_unit=time_names[num], time_number=int(timev)))
            return ", ".join(final_time)
        else:
            return change["logparams"]["duration"]  # Temporary? Should be rare? We will see in testing


@formatter.embed(event="block/block", mode="embed")
def embed_block_block(ctx, change):
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    user = change["title"].split(':', 1)[1]
    try:
        ipaddress.ip_address(user)
        embed["url"] = create_article_path("Special:Contributions/{user}".format(user=user))
    except ValueError:
        embed["url"] = create_article_path(sanitize_to_url(change["title"]))
    if "sitewide" not in change["logparams"]:
        restriction_description = ""
        if "restrictions" in change["logparams"]:
            if "pages" in change["logparams"]["restrictions"] and change["logparams"]["restrictions"]["pages"]:
                restriction_description = _("Blocked from editing the following pages: ")
                restricted_pages = ["*" + i["page_title"] + "*" for i in change["logparams"]["restrictions"]["pages"]]
                restriction_description = restriction_description + ", ".join(restricted_pages)
            if "namespaces" in change["logparams"]["restrictions"] and change["logparams"]["restrictions"][
                "namespaces"]:
                namespaces = []
                if restriction_description:
                    restriction_description = restriction_description + _(" and namespaces: ")
                else:
                    restriction_description = _("Blocked from editing pages on following namespaces: ")
                for namespace in change["logparams"]["restrictions"]["namespaces"]:
                    if str(namespace) in ctx.client.namespaces:  # if we have cached namespace name for given namespace number, add its name to the list
                        namespaces.append("*{ns}*".format(ns=ctx.client.namespaces[str(namespace)]["*"]))
                    else:
                        namespaces.append("*{ns}*".format(ns=namespace))
                restriction_description = restriction_description + ", ".join(namespaces)
            restriction_description = restriction_description + "."
            if len(restriction_description) > 1020:
                logger.debug(restriction_description)
                restriction_description = restriction_description[:1020] + "…"
            embed.add_field(_("Partial block details"), restriction_description, inline=True)
    block_flags = change["logparams"].get("flags")
    if block_flags:
        embed.add_field(_("Block flags"), ", ".join(
            block_flags))  # TODO Translate flags into MW messages, this requires making additional request in init_request since we want to get all messages with prefix (amprefix) block-log-flags- and that parameter is exclusive with ammessages
    embed["title"] = _("Blocked {blocked_user} {time}").format(blocked_user=user, time=block_expiry(change))
    embed_helper(ctx, embed, change)
    return embed


@formatter.compact(event="block/block", mode="compact")
def compact_block_block(ctx, change):
    user = change["title"].split(':', 1)[1]
    restriction_description = ""
    author, author_url = compact_author(ctx, change)
    parsed_comment = compact_summary(ctx)
    try:
        ipaddress.ip_address(user)
        link = clean_link(create_article_path("Special:Contributions/{user}".format(user=user)))
    except ValueError:
        link = clean_link(create_article_path(sanitize_to_url(change["title"])))
    else:
        if "sitewide" not in change["logparams"]:
            if "restrictions" in change["logparams"]:
                if "pages" in change["logparams"]["restrictions"] and change["logparams"]["restrictions"]["pages"]:
                    restriction_description = _(" on pages: ")
                    restricted_pages = ["*{page}*".format(page=i["page_title"]) for i in
                                        change["logparams"]["restrictions"]["pages"]]
                    restriction_description = restriction_description + ", ".join(restricted_pages)
                if "namespaces" in change["logparams"]["restrictions"] and change["logparams"]["restrictions"][
                    "namespaces"]:
                    namespaces = []
                    if restriction_description:
                        restriction_description = restriction_description + _(" and namespaces: ")
                    else:
                        restriction_description = _(" on namespaces: ")
                    for namespace in change["logparams"]["restrictions"]["namespaces"]:
                        if str(namespace) in ctx.client.namespaces:  # if we have cached namespace name for given namespace number, add its name to the list
                            namespaces.append("*{ns}*".format(ns=ctx.client.namespaces[str(namespace)]["*"]))
                        else:
                            namespaces.append("*{ns}*".format(ns=namespace))
                    restriction_description = restriction_description + ", ".join(namespaces)
                restriction_description = restriction_description + "."
                if len(restriction_description) > 1020:
                    logger.debug(restriction_description)
                    restriction_description = restriction_description[:1020] + "…"
    content = _(
        "[{author}]({author_url}) blocked [{user}]({user_url}) {time}{restriction_desc}{comment}").format(author=author,
                                                                                                          author_url=author_url,
                                                                                                          user=user,
                                                                                                          time=block_expiry(
                                                                                                              change),
                                                                                                          user_url=link,
                                                                                                          restriction_desc=restriction_description,
                                                                                                          comment=parsed_comment)
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)


# block/reblock - Changing settings of a block
@formatter.embed(event="block/reblock", mode="embed")
def embed_block_reblock(ctx, change):
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change)
    embed["url"] = create_article_path(sanitize_to_url(change["title"]))
    user = change["title"].split(':', 1)[1]
    embed["title"] = _("Changed block settings for {blocked_user}").format(blocked_user=sanitize_to_markdown(user))
    return embed


@formatter.compact(event="block/reblock")
def compact_block_reblock(ctx, change):
    author, author_url = compact_author(ctx, change)
    link = clean_link(create_article_path(sanitize_to_url(change["title"])))
    user = change["title"].split(':', 1)[1]
    parsed_comment = compact_summary(ctx)
    content = _("[{author}]({author_url}) changed block settings for [{blocked_user}]({user_url}){comment}").format(
        author=author, author_url=author_url, blocked_user=sanitize_to_markdown(user), user_url=link, comment=parsed_comment)
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)


# block/unblock - Unblocking an user

@formatter.embed(event="block/unblock", mode="embed")
def embed_block_unblock(ctx, change):
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change)
    embed["url"] = create_article_path(sanitize_to_url(change["title"]))
    user = change["title"].split(':', 1)[1]
    embed["title"] = _("Unblocked {blocked_user}").format(blocked_user=sanitize_to_markdown(user))
    return embed


@formatter.compact(event="block/unblock")
def compact_block_unblock(ctx, change):
    author, author_url = compact_author(ctx, change)
    link = clean_link(create_article_path(sanitize_to_url(change["title"])))
    user = change["title"].split(':', 1)[1]
    parsed_comment = compact_summary(ctx)
    content = _("[{author}]({author_url}) unblocked [{blocked_user}]({user_url}){comment}").format(author=author,
                                                                                                   author_url=author_url,
                                                                                                   blocked_user=sanitize_to_markdown(user),
                                                                                                   user_url=link,
                                                                                                   comment=parsed_comment)

    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)


# suppressed - Custom event for whenever there is limited information available about the event due to revdel


@formatter.embed(event="suppressed", mode="embed")
def embed_suppressed(ctx, change):
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed["url"] = create_article_path("")
    embed["title"] = _("Action has been hidden by administration")
    embed["author"]["name"] = _("Unknown")
    return embed


@formatter.compact(event="suppressed", mode="compact")
def compact_suppressed(ctx, change):
    content = _("An action has been hidden by administration.")
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)


# import/upload - Importing pages by uploading exported XML files

@formatter.embed(event="import/upload", mode="embed")
def embed_import_upload(ctx, change):
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change)
    embed["url"] = create_article_path(sanitize_to_url(change["title"]))
    embed["title"] = ngettext("Imported {article} with {count} revision",
                              "Imported {article} with {count} revisions", change["logparams"]["count"]).format(
        article=sanitize_to_markdown(change["title"]), count=change["logparams"]["count"])
    return embed


@formatter.compact(event="import/upload", mode="compact")
def compact_import_upload(ctx, change):
    link = clean_link(create_article_path(sanitize_to_url(change["title"])))
    author, author_url = compact_author(ctx, change)
    parsed_comment = compact_summary(ctx)
    content = ngettext("[{author}]({author_url}) imported [{article}]({article_url}) with {count} revision{comment}",
                       "[{author}]({author_url}) imported [{article}]({article_url}) with {count} revisions{comment}",
                       change["logparams"]["count"]).format(
        author=author, author_url=author_url, article=sanitize_to_markdown(change["title"]), article_url=link,
        count=change["logparams"]["count"], comment=parsed_comment)
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)


# import/interwiki - Importing interwiki entries


@formatter.embed(event="import/interwiki", mode="embed")
def embed_import_interwiki(ctx, change):
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change)
    embed["url"] = create_article_path(sanitize_to_url(change["title"]))
    embed["title"] = ngettext("Imported {article} with {count} revision from \"{source}\"",
                              "Imported {article} with {count} revisions from \"{source}\"",
                              change["logparams"]["count"]).format(
        article=sanitize_to_markdown(change["title"]), count=change["logparams"]["count"],
        source=sanitize_to_markdown(change["logparams"]["interwiki_title"]))
    return embed


@formatter.compact(event="import/interwiki", mode="compact")
def compact_import_interwiki(ctx, change):
    link = clean_link(create_article_path(sanitize_to_url(change["title"])))
    author, author_url = compact_author(ctx, change)
    source_link = clean_link(create_article_path(change["logparams"]["interwiki_title"]))
    parsed_comment = compact_summary(ctx)
    content = ngettext(
        "[{author}]({author_url}) imported [{article}]({article_url}) with {count} revision from [{source}]({source_url}){comment}",
        "[{author}]({author_url}) imported [{article}]({article_url}) with {count} revisions from [{source}]({source_url}){comment}",
        change["logparams"]["count"]).format(
        author=author, author_url=author_url, article=sanitize_to_markdown(change["title"]), article_url=link,
        count=change["logparams"]["count"], source=sanitize_to_markdown(change["logparams"]["interwiki_title"]),
        source_url=source_link,
        comment=parsed_comment)
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)


# rights/rights - Assigning rights groups
def get_changed_groups(change: dict) -> [[str], [str]]:
    """Creates strings comparing the changes between the user groups for the user"""
    def expiry_parse_time(passed_time):
        try:
            return _(" (until {date_and_time})").format(date_and_time=datetime.datetime.strptime(passed_time, "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d %H:%M:%S UTC"))
        except ValueError:
            return ""
    new_group_meta = {_(t["group"]): expiry_parse_time(t.get("expiry", "infinity")) for t in change["logparams"].get("newmetadata", [])}
    # translate all groups and pull them into a set
    old_groups = {_(x) for x in change["logparams"]["oldgroups"]}
    new_groups = {_(x) for x in change["logparams"]["newgroups"]}
    added = [x + new_group_meta.get(x, "") for x in new_groups - old_groups]
    removed = [x for x in old_groups - new_groups]
    return added, removed


@formatter.embed(event="rights/rights", aliases=["rights/autopromote"])
def embed_rights_rights(ctx, change):
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed["url"] = create_article_path(sanitize_to_url("User:{}".format(change["title"].split(":")[1])))
    if ctx.event == "rights/rights":
        embed["title"] = _("Changed group membership for {target}").format(target=sanitize_to_markdown(change["title"].split(":")[1]))
    else:
        embed.set_author(_("System"), "")
        embed["title"] = _("{target} got autopromoted to a new usergroup").format(
            target=sanitize_to_markdown(change["title"].split(":")[1]))
    # if len(change["logparams"]["oldgroups"]) < len(change["logparams"]["newgroups"]):
    #     embed["thumbnail"]["url"] = "https://i.imgur.com/WnGhF5g.gif"
    added, removed = get_changed_groups(change)
    if added:
        embed.add_field(ngettext("Added group", "Added groups", len(added)), "\n".join(added), inline=True)
    if removed:
        embed.add_field(ngettext("Removed group", "Removed groups", len(removed)), "\n".join(removed), inline=True)
    embed_helper(ctx, embed, change)
    return embed


@formatter.compact(event="rights/rights", aliases=["rights/autopromote"])
def compact_rights_rights(ctx, change):
    link = clean_link(create_article_path(sanitize_to_url("User:{user}".format(user=change["title"].split(":")[1]))))
    added, removed = get_changed_groups(change)
    author, author_url = compact_author(ctx, change)
    parsed_comment = compact_summary(ctx)
    if ctx.event == "rights/rights":
        group_changes = "Unknown group changes."  # Because I don't know if it can handle time extensions correctly
        if added and removed:
            group_changes = _("Added to {added} and removed from {removed}.").format(
                added=_(", ").join(added), removed=_(", ").join(removed))
        elif added:
            group_changes = _("Added to {added}.").format(added=_(", ").join(added))
        elif removed:
            group_changes = _("Removed from {removed}.").format(removed=_(", ").join(removed))
        content = _("[{author}]({author_url}) changed group membership for [{target}]({target_url}): {group_changes}{comment}").format(
            author=author, author_url=author_url, target=sanitize_to_markdown(change["title"].split(":")[1]),
            target_url=link, group_changes=group_changes, comment=parsed_comment)
    else:
        content = _("The system autopromoted [{target}]({target_url}) to {added}.{comment}").format(
            target=sanitize_to_markdown(change["title"].split(":")[1]), target_url=link,
            added=_(", ").join(added), comment=parsed_comment)
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)


# merge/merge - Merging histories of two pages

@formatter.embed(event="merge/merge", mode="embed")
def embed_merge_merge(ctx, change):
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change)
    embed["url"] = create_article_path(sanitize_to_url(change["title"]))
    embed["title"] = _("Merged revision histories of {article} into {dest}").format(
        article=sanitize_to_markdown(change["title"]),
        dest=sanitize_to_markdown(change["logparams"][
                                      "dest_title"]))
    return embed


@formatter.compact(event="merge/merge")
def compact_merge_merge(ctx, change):
    author, author_url = compact_author(ctx, change)
    parsed_comment = compact_summary(ctx)
    link = clean_link(create_article_path(sanitize_to_url(change["title"])))
    link_dest = clean_link(create_article_path(sanitize_to_url(change["logparams"]["dest_title"])))
    content = _(
        "[{author}]({author_url}) merged revision histories of [{article}]({article_url}) into [{dest}]({dest_url}){comment}").format(
        author=author, author_url=author_url, article=sanitize_to_markdown(change["title"]), article_url=link, dest_url=link_dest,
        dest=sanitize_to_markdown(change["logparams"]["dest_title"]), comment=parsed_comment)
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)


# newusers/autocreate - Auto creation of user account


@formatter.embed(event="newusers/autocreate", mode="embed")
def embed_newusers_autocreate(ctx, change):
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change)
    embed["url"] = create_article_path(sanitize_to_url(change["title"]))
    embed["title"] = _("Created account automatically")
    return embed


@formatter.compact(event="newusers/autocreate")
def compact_newusers_autocreate(ctx, change):
    author, author_url = compact_author(ctx, change)
    content = _("Account [{author}]({author_url}) was created automatically").format(author=author,
                                                                                     author_url=author_url)
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)


# newusers/create - Auto creation of user account


@formatter.embed(event="newusers/create", mode="embed")
def embed_newusers_create(ctx, change):
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change)
    embed["url"] = create_article_path(sanitize_to_url(change["title"]))
    embed["title"] = _("Created account")
    return embed


@formatter.compact(event="newusers/create")
def compact_newusers_create(ctx, change):
    author, author_url = compact_author(ctx, change)
    content = _("Account [{author}]({author_url}) was created").format(author=author, author_url=author_url)
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)


# newusers/autocreate - Auto creation of user account


@formatter.embed(event="newusers/create2", mode="embed")
def embed_newusers_create2(ctx, change):
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change)
    embed["url"] = create_article_path(sanitize_to_url(change["title"]))
    embed["title"] = _("Created account {article}").format(article=sanitize_to_markdown(change["title"]))
    return embed


@formatter.compact(event="newusers/create2")
def compact_newusers_create2(ctx, change):
    author, author_url = compact_author(ctx, change)
    parsed_comment = compact_summary(ctx)
    link = clean_link(create_article_path(sanitize_to_url(change["title"])))
    content = _("Account [{article}]({article_url}) was created by [{author}]({author_url}){comment}").format(
        article=sanitize_to_markdown(change["title"]), article_url=link, author=author, author_url=author_url, comment=parsed_comment)
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)


# newusers/byemail - Creation of account by email


@formatter.embed(event="newusers/byemail", mode="embed")
def embed_newusers_byemail(ctx, change):
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change)
    embed["url"] = create_article_path(sanitize_to_url(change["title"]))
    embed["title"] = _("Created account {article} and password was sent by email").format(
        article=sanitize_to_markdown(change["title"]))
    return embed


@formatter.compact(event="newusers/byemail")
def compact_newusers_byemail(ctx, change):
    author, author_url = compact_author(ctx, change)
    parsed_comment = compact_summary(ctx)
    link = clean_link(create_article_path(sanitize_to_url(change["title"])))
    content = _(
        "Account [{article}]({article_url}) was created by [{author}]({author_url}) and password was sent by email{comment}").format(
        article=sanitize_to_markdown(change["title"]), article_url=link, author=author, author_url=author_url, comment=parsed_comment)
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)


# newusers/newusers - New users


@formatter.embed(event="newusers/newusers", mode="embed")
def embed_newusers_newusers(ctx, change):
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change)
    embed["url"] = create_article_path(sanitize_to_url("User:{}".format(change["user"])))
    embed["title"] = _("Created account")
    return embed


@formatter.compact(event="newusers/newusers")
def compact_newusers_newusers(ctx, change):
    author, author_url = compact_author(ctx, change)
    content = _("Account [{author}]({author_url}) was created").format(author=author, author_url=author_url)
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)


# newusers/reclaim - New user reclaimed


@formatter.embed(event="newusers/reclaim", mode="embed")
def embed_newusers_reclaim(ctx, change):
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change)
    embed["url"] = create_article_path(sanitize_to_url("User:{}".format(change["user"])))
    embed["title"] = _("Reclaimed account")
    return embed


@formatter.compact(event="newusers/reclaim")
def compact_newusers_reclaim(ctx, change):
    author, author_url = compact_author(ctx, change)
    content = _("Account [{author}]({author_url}) was reclaimed").format(author=author, author_url=author_url)
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)


# contentmodel/change - Changing the content model of a page


@formatter.embed(event="contentmodel/change", mode="embed")
def embed_contentmodel_change(ctx, change):
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change, set_desc=False)
    embed["url"] = create_article_path(sanitize_to_url(change["title"]))
    embed["title"] = _("Changed the content model of the page {article}").format(
        article=sanitize_to_markdown(change["title"]))
    embed["description"] = _("Model changed from {old} to {new}: {reason}").format(old=change["logparams"]["oldmodel"],
                                                                                   new=change["logparams"]["newmodel"],
                                                                                   reason=ctx.parsedcomment)
    return embed


@formatter.compact(event="contentmodel/change")
def compact_contentmodel_change(ctx, change):
    author, author_url = compact_author(ctx, change)
    link = clean_link(create_article_path(sanitize_to_url(change["title"])))
    parsed_comment = compact_summary(ctx)
    content = _(
        "[{author}]({author_url}) changed the content model of the page [{article}]({article_url}) from {old} to {new}{comment}").format(
        author=author, author_url=author_url, article=sanitize_to_markdown(change["title"]), article_url=link,
        old=change["logparams"]["oldmodel"],
        new=change["logparams"]["newmodel"], comment=parsed_comment)
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)


# contentmodel/new - Creating a page with non-default content model


@formatter.embed(event="contentmodel/new", mode="embed")
def embed_contentmodel_new(ctx, change):
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change, set_desc=False)
    embed["url"] = create_article_path(sanitize_to_url(change["title"]))
    embed["title"] = _("Created the page {article} using a non-default content model").format(
        article=sanitize_to_markdown(change["title"]))
    embed["description"] = _("Created with model {new}: {reason}").format(new=change["logparams"]["newmodel"],
                                                                          reason=ctx.parsedcomment)
    return embed


@formatter.compact(event="contentmodel/new")
def compact_contentmodel_new(ctx, change):
    author, author_url = compact_author(ctx, change)
    link = clean_link(create_article_path(sanitize_to_url(change["title"])))
    parsed_comment = compact_summary(ctx)
    content = _(
        "[{author}]({author_url}) created the page [{article}]({article_url}) using a non-default content model {new}{comment}").format(
        author=author, author_url=author_url, article=sanitize_to_markdown(change["title"]), article_url=link,
        new=change["logparams"]["newmodel"], comment=parsed_comment)
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)


# managetags/create - Creating log tags


@formatter.embed(event="managetags/create", mode="embed")
def embed_managetags_create(ctx, change):
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change)
    ctx.client.refresh_internal_data()
    embed["url"] = create_article_path(sanitize_to_url(change["title"]))
    embed["title"] = _("Created the tag \"{tag}\"").format(tag=sanitize_to_markdown(change["logparams"]["tag"]))
    return embed


@formatter.compact(event="managetags/create")
def compact_managetags_create(ctx, change):
    author, author_url = compact_author(ctx, change)
    link = clean_link(create_article_path(sanitize_to_url(change["title"])))
    ctx.client.refresh_internal_data()
    parsed_comment = compact_summary(ctx)
    content = _("[{author}]({author_url}) created the [tag]({tag_url}) \"{tag}\"{comment}").format(author=author,
                                                                                                   author_url=author_url,
                                                                                                   tag=
                                                                                                   sanitize_to_markdown(
                                                                                                       change[
                                                                                                           "logparams"][
                                                                                                           "tag"]),
                                                                                                   tag_url=link,
                                                                                                   comment=parsed_comment)

    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)


# managetags/delete - Deleting a tag


@formatter.embed(event="managetags/delete", mode="embed")
def embed_managetags_delete(ctx, change):
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    ctx.client.refresh_internal_data()
    embed["url"] = create_article_path(sanitize_to_url(change["title"]))
    embed["title"] = _("Deleted the tag \"{tag}\"").format(tag=sanitize_to_markdown(change["logparams"]["tag"]))
    if change["logparams"]["count"] > 0:
        embed.add_field(_('Removed from'), ngettext("{} revision or log entry", "{} revisions and/or log entries",
                                                    change["logparams"]["count"]).format(change["logparams"]["count"]))
    embed_helper(ctx, embed, change)
    return embed


@formatter.compact(event="managetags/delete")
def compact_managetags_delete(ctx, change):
    author, author_url = compact_author(ctx, change)
    link = clean_link(create_article_path(sanitize_to_url(change["title"])))
    ctx.client.refresh_internal_data()
    parsed_comment = compact_summary(ctx)
    if change["logparams"]["count"] == 0:
        content = _("[{author}]({author_url}) deleted the [tag]({tag_url}) \"{tag}\"{comment}").format(author=author,
                                                                                                       author_url=author_url,
                                                                                                       tag=sanitize_to_markdown(
                                                                                                           change[
                                                                                                               "logparams"][
                                                                                                               "tag"]),
                                                                                                       tag_url=link,
                                                                                                       comment=parsed_comment)
    else:
        content = ngettext(
            "[{author}]({author_url}) deleted the [tag]({tag_url}) \"{tag}\" and removed it from {count} revision or log entry{comment}",
            "[{author}]({author_url}) deleted the [tag]({tag_url}) \"{tag}\" and removed it from {count} revisions and/or log entries{comment}",
            change["logparams"]["count"]).format(author=author, author_url=author_url,
                                                 tag=sanitize_to_markdown(change["logparams"]["tag"]),
                                                 tag_url=link, count=change["logparams"]["count"],
                                                 comment=parsed_comment)
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)


# managetags/activate - Activating a tag


@formatter.embed(event="managetags/activate", mode="embed")
def embed_managetags_activate(ctx, change):
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change)
    embed["url"] = create_article_path(sanitize_to_url(change["title"]))
    embed["title"] = _("Activated the tag \"{tag}\"").format(tag=sanitize_to_markdown(change["logparams"]["tag"]))
    return embed


@formatter.compact(event="managetags/activate")
def compact_managetags_activate(ctx, change):
    author, author_url = compact_author(ctx, change)
    link = clean_link(create_article_path(sanitize_to_url(change["title"])))
    parsed_comment = compact_summary(ctx)
    content = _("[{author}]({author_url}) activated the [tag]({tag_url}) \"{tag}\"{comment}").format(author=author,
                                                                                                     author_url=author_url,
                                                                                                     tag=sanitize_to_markdown(
                                                                                                         change[
                                                                                                             "logparams"][
                                                                                                             "tag"]),
                                                                                                     tag_url=link,
                                                                                                     comment=parsed_comment)
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)


# managetags/deactivate - Deactivating a tag


@formatter.embed(event="managetags/deactivate", mode="embed")
def embed_managetags_deactivate(ctx, change):
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change)
    embed["url"] = create_article_path(sanitize_to_url(change["title"]))
    embed["title"] = _("Deactivated the tag \"{tag}\"").format(tag=sanitize_to_markdown(change["logparams"]["tag"]))
    return embed


@formatter.compact(event="managetags/deactivate")
def compact_managetags_deactivate(ctx, change):
    author, author_url = compact_author(ctx, change)
    link = clean_link(create_article_path(sanitize_to_url(change["title"])))
    parsed_comment = compact_summary(ctx)
    content = _("[{author}]({author_url}) deactivated the [tag]({tag_url}) \"{tag}\"{comment}").format(author=author,
                                                                                                       author_url=author_url,
                                                                                                       tag=sanitize_to_markdown(
                                                                                                           change[
                                                                                                               "logparams"][
                                                                                                               "tag"]),
                                                                                                       tag_url=link,
                                                                                                       comment=parsed_comment)
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)
