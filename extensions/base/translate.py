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
    clean_link, compact_summary

_ = formatters_i18n.gettext
ngettext = formatters_i18n.ngettext

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
    parsed_comment = compact_summary(ctx)
    content = _("[{author}]({author_url}) marked [{article}]({article_url}) for translation{comment}").format(
        author=author, author_url=author_url,
        article=sanitize_to_markdown(change["title"]), article_url=link,
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
    parsed_comment = compact_summary(ctx)
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
    parsed_comment = compact_summary(ctx)
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
    parsed_comment = compact_summary(ctx)
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
    parsed_comment = compact_summary(ctx)
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
    parsed_comment = compact_summary(ctx)
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
    parsed_comment = compact_summary(ctx)
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

# pagetranslation/encourage - Encouraging to translate an article


@formatter.embed(event="pagetranslation/encourage")
def embed_pagetranslation_encourage(ctx: Context, change: dict):
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change)
    embed["url"] = create_article_path(sanitize_to_url(change["title"]))
    embed["title"] = _("Encouraged translation of \"{article}\"").format(article=sanitize_to_markdown(change["title"]))
    return embed


@formatter.compact(event="pagetranslation/encourage")
def compact_pagetranslation_encourage(ctx: Context, change: dict):
    author, author_url = compact_author(ctx, change)
    parsed_comment = compact_summary(ctx)
    link = clean_link(create_article_path(sanitize_to_url(change["title"])))
    content = _("[{author}]({author_url}) encouraged translation of [{article}]({article_url}){comment}").format(
        author=author, author_url=author_url,
        article=sanitize_to_markdown(change["title"]), article_url=link,
        comment=parsed_comment
    )
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)

# pagetranslation/discourage - Discouraging to translate an article


@formatter.embed(event="pagetranslation/discourage")
def embed_pagetranslation_discourage(ctx: Context, change: dict):
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change)
    embed["url"] = create_article_path(sanitize_to_url(change["title"]))
    embed["title"] = _("Discouraged translation of \"{article}\"").format(article=sanitize_to_markdown(change["title"]))
    return embed


@formatter.compact(event="pagetranslation/discourage")
def compact_pagetranslation_discourage(ctx: Context, change: dict):
    author, author_url = compact_author(ctx, change)
    parsed_comment = compact_summary(ctx)
    link = clean_link(create_article_path(sanitize_to_url(change["title"])))
    content = _("[{author}]({author_url}) discouraged translation of [{article}]({article_url}){comment}").format(
        author=author, author_url=author_url,
        article=sanitize_to_markdown(change["title"]), article_url=link,
        comment=parsed_comment
    )
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)

# pagetranslation/prioritylanguages - Changing the priority of translations?


@formatter.embed(event="pagetranslation/prioritylanguages")
def embed_pagetranslation_prioritylanguages(ctx: Context, change: dict):
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change)
    embed["url"] = create_article_path(sanitize_to_url(change["title"]))
    if "languages" in change["logparams"]:
        languages = "`, `".join(change["logparams"]["languages"].split(","))
        if change["logparams"]["force"] == "on":
            embed["title"] = _("Limited languages for \"{article}\" to `{languages}`").format(article=sanitize_to_markdown(change["title"]),
                                                                                              languages=languages)
        else:
            embed["title"] = _("Priority languages for \"{article}\" set to `{languages}`").format(
                article=sanitize_to_markdown(change["title"]), languages=languages)
    else:
        embed["title"] = _("Removed priority languages from \"{article}\"").format(article=sanitize_to_markdown(change["title"]))
    return embed


@formatter.compact(event="pagetranslation/prioritylanguages")
def compact_pagetranslation_prioritylanguages(ctx: Context, change: dict):
    author, author_url = compact_author(ctx, change)
    parsed_comment = compact_summary(ctx)
    link = clean_link(create_article_path(sanitize_to_url(change["title"])))
    if "languages" in change["logparams"]:
        languages = "`, `".join(change["logparams"]["languages"].split(","))
        if change["logparams"]["force"] == "on":
            content = _(
                "[{author}]({author_url}) limited languages for [{article}]({article_url}) to `{languages}`{comment}").format(
                author=author, author_url=author_url,
                article=sanitize_to_markdown(change["title"]), article_url=link,
                languages=languages, comment=parsed_comment
            )
        else:
            content = _(
                "[{author}]({author_url}) set the priority languages for [{article}]({article_url}) to `{languages}`{comment}").format(
                author=author, author_url=author_url,
                article=sanitize_to_markdown(change["title"]), article_url=link,
                languages=languages, comment=parsed_comment
            )
    else:
        content = _(
            "[{author}]({author_url}) removed priority languages from [{article}]({article_url}){comment}").format(
            author=author, author_url=author_url,
            article=sanitize_to_markdown(change["title"]), article_url=link,
            comment=parsed_comment
        )
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)


# pagetranslation/associate - Adding an article to translation group


@formatter.embed(event="pagetranslation/associate")
def embed_pagetranslation_associate(ctx: Context, change: dict):
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change)
    embed["url"] = create_article_path(sanitize_to_url(change["title"]))
    embed["title"] = _("Added translatable page \"{article}\" to aggregate group \"{group}\"").format(
        article=sanitize_to_markdown(change["title"]), group=change["logparams"]["aggregategroup"])
    return embed


@formatter.compact(event="pagetranslation/associate")
def compact_pagetranslation_associate(ctx: Context, change: dict):
    author, author_url = compact_author(ctx, change)
    parsed_comment = compact_summary(ctx)
    link = clean_link(create_article_path(sanitize_to_url(change["title"])))
    content = _(
        "[{author}]({author_url}) added translatable page [{article}]({article_url}) to aggregate group \"{group}\"{comment}").format(
        author=author, author_url=author_url,
        article=sanitize_to_markdown(change["title"]), article_url=link,
        group=change["logparams"]["aggregategroup"], comment=parsed_comment
    )
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)

# pagetranslation/dissociate - Removing an article from translation group


@formatter.embed(event="pagetranslation/dissociate")
def embed_pagetranslation_dissociate(ctx: Context, change: dict):
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change)
    embed["url"] = create_article_path(sanitize_to_url(change["title"]))
    embed["title"] = _("Removed translatable page \"{article}\" from aggregate group \"{group}\"").format(
        article=sanitize_to_markdown(change["title"]), group=change["logparams"]["aggregategroup"])
    return embed


@formatter.compact(event="pagetranslation/dissociate")
def compact_pagetranslation_dissociate(ctx: Context, change: dict):
    author, author_url = compact_author(ctx, change)
    parsed_comment = compact_summary(ctx)
    link = clean_link(create_article_path(sanitize_to_url(change["title"])))
    content = _(
        "[{author}]({author_url}) removed translatable page [{article}]({article_url}) from aggregate group \"{group}\"{comment}").format(
        author=author, author_url=author_url,
        article=sanitize_to_markdown(change["title"]), article_url=link,
        group=change["logparams"]["aggregategroup"], comment=parsed_comment
    )
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)

# translationreview/message - Reviewing translation


@formatter.embed(event="translationreview/message")
def embed_translationreview_message(ctx: Context, change: dict):
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change)
    link = create_article_path(sanitize_to_url(change["title"]))
    if "?" in link:
        embed["url"] = link + "&oldid={}".format(change["logparams"]["revision"])
    else:
        embed["url"] = link + "?oldid={}".format(change["logparams"]["revision"])
    embed["title"] = _("Reviewed translation \"{article}\"").format(article=sanitize_to_markdown(change["title"]))
    return embed


@formatter.compact(event="translationreview/message")
def compact_translationreview_message(ctx: Context, change: dict):
    author, author_url = compact_author(ctx, change)
    parsed_comment = compact_summary(ctx)
    link = create_article_path(sanitize_to_url(change["title"]))
    if "?" in link:
        link = link + "&oldid={}".format(change["logparams"]["revision"])
    else:
        link = link + "?oldid={}".format(change["logparams"]["revision"])
    link = clean_link(link)
    content = _("[{author}]({author_url}) reviewed translation [{article}]({article_url}){comment}").format(
        author=author, author_url=author_url,
        article=sanitize_to_markdown(change["title"]), article_url=link,
        comment=parsed_comment
    )
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)

# translationreview/group - Changing of state for group translation?


@formatter.embed(event="translationreview/group")
def embed_translationreview_group(ctx: Context, change: dict):
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change)
    embed["url"] = create_article_path(sanitize_to_url(change["title"]))
    embed["title"] = _("Changed the state of `{language}` translations of \"{article}\"").format(
        language=change["logparams"]["language"], article=sanitize_to_markdown(change["title"]))
    if "old-state" in change["logparams"]:
        embed.add_field(_("Old state"), change["logparams"]["old-state"], inline=True)
    embed.add_field(_("New state"), change["logparams"]["new-state"], inline=True)
    return embed


@formatter.compact(event="translationreview/group")
def compact_translationreview_group(ctx: Context, change: dict):
    author, author_url = compact_author(ctx, change)
    parsed_comment = compact_summary(ctx)
    link = clean_link(create_article_path(sanitize_to_url(change["title"])))
    if "old-state" in change["logparams"]:
        content = _(
            "[{author}]({author_url}) changed the state of `{language}` translations of [{article}]({article_url}) from `{old_state}` to `{new_state}`{comment}").format(
            author=author, author_url=author_url, language=change["logparams"]["language"],
            article=sanitize_to_markdown(change["logparams"]["group-label"]), article_url=link,
            old_state=change["logparams"]["old-state"], new_state=change["logparams"]["new-state"],
            comment=parsed_comment
        )
    else:
        content = _(
            "[{author}]({author_url}) changed the state of `{language}` translations of [{article}]({article_url}) to `{new_state}`{comment}").format(
            author=author, author_url=author_url, language=change["logparams"]["language"],
            article=sanitize_to_markdown(change["logparams"]["group-label"]), article_url=link,
            new_state=change["logparams"]["new-state"], comment=parsed_comment
        )
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)

# pagelang/pagelang - Changing the language of a page


def get_languages(change):
    old_lang = "`{}`".format(change["logparams"]["oldlanguage"])
    if change["logparams"]["oldlanguage"][-5:] == "[def]":
        old_lang = "`{}` {}".format(change["logparams"]["oldlanguage"][:-5], _("(default)"))
    new_lang = "`{}`".format(change["logparams"]["newlanguage"])
    if change["logparams"]["newlanguage"][-5:] == "[def]":
        new_lang = "`{}` {}".format(change["logparams"]["oldlanguage"][:-5], _("(default)"))
    return old_lang, new_lang

@formatter.embed(event="pagelang/pagelang")
def embed_pagelang_pagelang(ctx: Context, change: dict):
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    embed_helper(ctx, embed, change)
    embed["url"] = create_article_path(sanitize_to_url(change["title"]))
    old_lang, new_lang = get_languages(change)
    embed["title"] = _("Changed the language of \"{article}\"").format(article=sanitize_to_markdown(change["title"]))
    embed.add_field(_("Old language"), old_lang, inline=True)
    embed.add_field(_("New language"), new_lang, inline=True)
    return embed


@formatter.compact(event="pagelang/pagelang")
def compact_pagelang_pagelang(ctx: Context, change: dict):
    author, author_url = compact_author(ctx, change)
    parsed_comment = compact_summary(ctx)
    link = clean_link(create_article_path(sanitize_to_url(change["title"])))
    old_lang, new_lang = get_languages(change)
    content = _(
        "[{author}]({author_url}) changed the language of [{article}]({article_url}) from {old_lang} to {new_lang}{comment}").format(
        author=author, author_url=author_url,
        article=sanitize_to_markdown(change["title"]), article_url=link,
        old_lang=old_lang, new_lang=new_lang, comment=parsed_comment
    )
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)
