#!/usr/bin/env python3
from typing import Final, List, Optional

import aiohttp
import pycountry
from urllib.parse import quote as q
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, InputMessagePhoto, InputMessagePhotoFileID
from pyrogram.raw.functions.messages import (
    SendMediaCommand,
    SendMessageCommand,
    EditMessageTextCommand,
    DeleteMessagesCommand,
    DeleteMessageCommand,
)
from pyrogram.raw.types import (
    InputMessageContent,
    InputMedia,
)
from pyrogram.errors import MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty, ReplyMarkupInvalid
from pyrogram.filters import command, regex, ChatTypeFilter
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from bot import LOGGER, bot, config_dict, user_data
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import send_message, edit_message
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker

LIST_ITEMS: Final = 4
IMDB_GENRE_EMOJI: Final = {
    "Action": "🚀",
    "Adult": "🔞",
    "Adventure": "🌋",
    "Animation": "🎠",
    "Biography": "📜",
    "Comedy": "🪗",
    "Crime": "🔪",
    "Documentary": "🎞",
    "Drama": "🎭",
    "Family": "👨‍👩‍👧‍👦",
    "Fantasy": "🫧",
    "Film Noir": "🎯",
    "Game Show": "🎮",
    "History": "🏛",
    "Horror": "🧟",
    "Musical": "🎻",
    "Music": "🎸",
    "Mystery": "🧳",
    "News": "📰",
    "Reality-TV": "🖥",
    "Romance": "🥰",
    "Sci-Fi": "🌠",
    "Short": "📝",
    "Sport": "⛳",
    "Talk-Show": "👨‍🍳",
    "Thriller": "🗡",
    "War": "⚔",
    "Western": "🪩",
}
MDL_API: Final = "http://kuryana.vercel.app/"  # Public API ! Do Not Abuse !

async def mydramalist_search(client, message):
    if " " in message.text:
        temp_message = await send_message(message, "<i>Searching in MyDramaList ...</i>")
        title = message.text.split(" ", 1)[1]
        user_id = message.from_user.id
        buttons = ButtonMaker()

        async with aiohttp.ClientSession() as session:
            async with session.request(
                "GET",
                f"{MDL_API}/search/q/{q(title)}",
            ) as resp:
                if resp.status != 200:
                    return await edit_message(temp_message, "<i>No Results Found</i>, Try Again or Use <b>MyDramaList Link</b>")
                mdl = await resp.json()

        for drama in mdl["results"]["dramas"]:
            buttons.ibutton(
                f"🎬 {drama.get('title')} ({drama.get('year')})",
                f"mdl {user_id} drama {drama.get('slug')}",
            )

        buttons.ibutton("🚫 Close 🚫", f"mdl {user_id} close")
        await edit_message(
            temp_message,
            '<b><i>Dramas found on MyDramaList :</i></b>',
            buttons.build_menu(1),
        )
    else:
        await send_message(message, f'<i>Send Movie / TV Series Name along with /{BotCommands.MyDramaListCommand} Command</i>')


async def extract_mdl(slug):
    async with aiohttp.ClientSession() as session:
        async with session.request(
            "GET",
            f"{MDL_API}/id/{slug}",
        ) as resp:
            mdl = (await resp.json())["data"]

    plot = mdl.get("synopsis")
    if plot and len(plot) > 300:
        plot = f"{plot[:300]}..."

    return {
        "title": mdl.get("title"),
        "score": mdl["details"].get("score"),
        "aka": list_to_str(mdl.get("also_known_as")),
        "episodes": mdl["details"].get("episodes"),
        "type": mdl["details"].get("type"),
        "cast": list_to_str(mdl.get("casts"), cast=True),
        "country": list_to_hash([mdl["details"].get("country")], True),
        "aired_date": mdl["details"].get("aired", "N/A"),
        "aired_on": mdl["details"].get("aired_on"),
        "org_network": mdl["details"].get("original_network"),
        "duration": mdl["details"].get("duration"),
        "watchers": mdl["details"].get("watchers"),
        "ranked": mdl["details"].get("ranked"),
        "popularity": mdl["details"].get("popularity"),
        "related_content": list_to_str(mdl["others"].get("related_content")),
        "native_title": list_to_str(mdl["others"].get("native_title")),
        "director": list_to_str(mdl["others"].get("director")),
        "screenwriter": list_to_str(mdl["others"].get("screenwriter")),
        "genres": list_to_hash(mdl["others"].get("genres"), emoji=True),
        "tags": list_to_str(mdl["others"].get("tags")),
        "poster": mdl.get("poster").replace("c.jpg?v=1", "f.jpg?v=1").strip(),
        "synopsis": plot,
        "rating": f"{mdl.get('rating')} / 10",
        "content_rating": mdl["details"].get("content_rating"),
        "url": mdl.get("link"),
    }


def list_to_str(k, cast=False):
    if not k:
        return ""
    elif len(k) == 1:
        return str(k[0])
    elif LIST_ITEMS:
        k = k[:int(LIST_ITEMS)]
    if cast:
        return " ".join(
            f'<a href="{elem.get("link")}">{elem.get("name")}</a>,' for elem in k
        )[:-1]
    return " ".join(f"{elem}," for elem in k)[:-1]


def list_to_hash(k, flagg=False, emoji=False):
    listing = ""
    if not k:
        return ""
    elif len(k) == 1:
        if not flagg:
            if emoji:
                return str(IMDB_GENRE_EMOJI.get(k[0], '') + " #" + k[0].replace(" ", "_").replace("-", "_"))
            return str("#" + k[0].replace(" ", "_").replace("-", "_"))
        try:
            conflag = (pycountry.countries.get(name=k[0])).flag
            return str(f"{conflag} #" + k[0].replace(" ", "_").replace("-", "_"))
        except AttributeError:
            return str("#" + k[0].replace(" ", "_").replace("-", "_"))
    elif LIST_ITEMS:
        k = k[:int(LIST_ITEMS)]
        for elem in k:
            ele = elem.replace(" ", "_").replace("-", "_")
            if flagg:
                with suppress(AttributeError):
                    conflag = (pycountry.countries.get(name=elem)).flag
                    listing += f"{conflag} "
            if emoji:
                listing += f"{IMDB_GENRE_EMOJI.get(elem, '')} "
            listing += f"#{ele}, "
        return f"{listing[:-2]}"
    else:
        for elem in k:
            ele = elem.replace(" ", "_").replace("-", "_")
            if flagg:
                conflag = (pycountry.countries.get(name=elem)).flag
                listing += f"{conflag} "
            listing += f"#{ele}, "
        return listing[:-2]


async def mdl_callback(client, query):
    message = query.message
    user_id = query.from_user.id
    data = query.data.split()

    if user_id != int(data[1]):
        await query.answer("Not Yours!", show_alert=True)
    elif data[2] == "drama":
        await query.answer()
        mdl = await extract_mdl(data[3])
        buttons = ButtonMaker()
        buttons.ibutton("🚫 Close 🚫", f"mdl {user_id} close")

        template = config_dict["MDL_TEMPLATE"]
        if mdl and template != "":
            cap = template.format(**mdl)
        else:
            cap = "<i>No Data Received</i>"

        if mdl.get("poster"):
            try:
                input_media = InputMediaPhoto(
                    media=InputMediaPhotoFileID(mdl["poster"]),
                    caption=cap,
                )
                await client.send(
                    SendMediaCommand(
                        chat_id=message.chat.id,
                        reply_to_message_id=message.reply_to_message.message_id,
                        media=input_media,
                        reply_markup=InlineKeyboardMarkup(buttons.build_menu(1)),
                    )
                )
            except (MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty):
                poster = mdl["poster"].replace("f.jpg?v=1", "c.jpg?v=1")
                input_media = InputMediaPhoto(
                    media=InputMediaPhotoFileID(poster),
                    caption=cap,
                )
                await client.send(
                    SendMessageCommand(
                        chat_id=message.chat.id,
                        reply_to_message_id=message.reply_to_message.message_id,
                        input_message_content=InputMessageContent(
                            message_text=cap,
                            parse_mode="HTML",
                            disable_web_page_preview=True,
                        ),
                        reply_markup=InlineKeyboardMarkup(buttons.build_menu(1)),
                       
