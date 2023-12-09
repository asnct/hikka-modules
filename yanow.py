__version__ = (2, 0, 0)

#  Updated module for yandex music.
#  Copyright (C) 2023  ASNCT

#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.

#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.

#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.

# requires: git+https://github.com/MarshalX/yandex-music-api@dev
# meta desc: Module for yandex music. Based on SpotifyNow.

import functools
import logging
from asyncio import sleep
from types import FunctionType

import aiohttp
from telethon import TelegramClient
from telethon.errors.rpcerrorlist import FloodWaitError
from telethon.tl.functions.account import UpdateProfileRequest
from telethon.tl.types import Message
from yandex_music import ClientAsync

from .. import loader, utils

logger = logging.getLogger(__name__)
logging.getLogger("yandex_music").propagate = False


@loader.tds
class YaNowMod(loader.Module):
    """Module for work with Yandex Music. Based on SpotifyNow."""

    strings = {
        "name": "YaNow",
        "no_token": "<b>🚫 Specify a token in config!</b>",
        "playing": "<b>🎧 Now playing: </b><code>{}</code><b> - </b><code>{}</code>",
        "no_args": "<b>🚫 Provide arguments!</b>",
        "autobio_enabled": "<b>🔁 Autobio enabled</b>",
        "autobio_disabled": "<b>🔁 Autobio disabled</b>",
        "lyrics": "<b>📜 Lyrics: \n{}</b>",
        "already_liked": "<b>🚫 Current playing track is already liked!</b>",
        "liked": "<b>❤ Liked current playing track!</b>",
        "not_liked": "<b>🚫 Current playing track not liked!</b>",
        "disliked": "<b>💔 Disliked current playing track!</b>",
        "radio_error": '<b>🌊 You listening to track in "My Vibe", i can\'t recognize it.</b>',
        "_cfg_token": "Yandex.Music account token",
        "_cfg_autobio_template": "Template for AutoBio",
        "no_lyrics": "<b>🚫 Track doesn't have lyrics.</b>",
        "guide": (
            '<a href="https://github.com/MarshalX/yandex-music-api/discussions/513#discussioncomment-2729781">'
            "Instructions for obtaining a Yandex.Music token</a>"
        ),
    }

    strings_ru = {
        "no_token": "<b>🚫 Укажи токен в конфиге!</b>",
        "playing": "<b>🎧 Сейчас играет: </b><code>{}</code><b> - </b><code>{}</code>",
        "no_args": "<b>🚫 Укажи аргументы!</b>",
        "autobio_enabled": "<b>🔁 Autobio включен</b>",
        "autobio_disabled": "<b>🔁 Autobio выключен</b>",
        "lyrics": "<b>📜 Текст песни: \n{}</b>",
        "_cls_doc": "Модуль для Яндекс.Музыка. Основан на SpotifyNow.",
        "already_liked": "<b>🚫 Текущий трек уже лайкнут!</b>",
        "liked": "<b>❤ Лайкнул текущий трек!</b>",
        "not_liked": "<b>🚫 Текущий трек не лайкнут!</b>",
        "disliked": "<b>💔 Дизлайкнул текущий трек!</b>",
        "radio_error": "<b>🌊 Ты слушаешь трек в Моей Волне, я не могу распознать его.</b>",
        "_cfg_token": "Токен аккаунта Яндекс.Музыка",
        "_cfg_autobio_template": "Шаблон для AutoBio",
        "no_lyrics": "<b>🚫 У трека нет текста!</b>",
        "guide": (
            '<a href="https://github.com/MarshalX/yandex-music-api/discussions/513#discussioncomment-2729781">'
            "Инструкция по получению токена Яндекс.Музыка</a>"
        ),
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "token",
                None,
                lambda: self.strings["_cfg_token"],
                validator=loader.validators.Hidden(),
            ),
            loader.ConfigValue(
                "autobio_template",
                "🎧 {artists} - {title}",
                lambda: self.strings["_cfg_autobio_template"],
                validator=loader.validators.String(),
            ),
        )

    async def on_dlmod(self):
        if not self.get("guide_send", False):
            await self.inline.bot.send_message(
                self._tg_id,
                self.strings["guide"],
            )
            self.set("guide_send", True)

    async def client_ready(self, client: TelegramClient, db):
        self.client = client
        self.db = db

        self._premium = getattr(await self.client.get_me(), "premium", False)

        if self.get("autobio", False):
            self.autobio.start()

    def authorized(func) -> FunctionType:
        @functools.wraps(func)
        async def wrapped(*args, **kwargs):
            try:
                client = await ClientAsync(args[0].config["token"]).init()
            except Exception:
                await utils.answer(args[1], args[0].strings("no_token"))
                return

            kwargs["client"] = client

            return await func(*args, **kwargs)

        wrapped.__doc__ = func.__doc__
        wrapped.__module__ = func.__module__

        return wrapped

    @authorized
    @loader.command(
        ru_doc="Получить текущий трек",
    )
    async def ynowcmd(self, message: Message, client: ClientAsync):
        """Get now playing track"""
        try:
            queues = await client.queues_list()
            last_queue = await client.queue(queues[0].id)

            last_track_id = last_queue.get_current_track()
            last_track = await last_track_id.fetch_track_async()
        except Exception:
            await utils.answer(message, self.strings["radio_error"])
            return

        info = await client.tracks_download_info(last_track.id, True)
        link = info[0].direct_link

        artists = ", ".join(last_track.artists_name())
        title = last_track.title + (
            f" ({last_track.version})" if last_track.version else ""
        )

        caption = self.strings["playing"].format(
            utils.escape_html(artists),
            utils.escape_html(title),
        )

        await self.inline.form(
            message=message,
            text=caption,
            silent=True,
            audio={
                "url": link,
                "title": utils.escape_html(title),
                "performer": utils.escape_html(artists),
            },
        )

    @authorized
    @loader.command(
        ru_doc="Получить текст текущей песни",
    )
    async def ylyrics(self, message: Message, client: ClientAsync):
        """Get now playing track lyrics"""
        try:
            queues = await client.queues_list()
            last_queue = await client.queue(queues[0].id)

            last_track_id = last_queue.get_current_track()
            last_track = await last_track_id.fetch_track_async()
        except Exception:
            await utils.answer(message, self.strings["radio_error"])
            return

        try:
            track_lyrics = await client.tracks_lyrics(last_track.id)
            async with aiohttp.ClientSession() as session:
                async with session.get(track_lyrics.download_url) as request:
                    lyrics = await request.text()

            text = self.strings["lyrics"].format(utils.escape_html(lyrics))
        except Exception:
            text = self.strings["no_lyrics"]

        await utils.answer(message, text)

    @authorized
    @loader.command(
        ru_doc="Отображение текущей песни в описании аккаунта",
    )
    async def ybio(self, message: Message, client: ClientAsync):
        """Show now playing track in your bio"""
        current = self.get("autobio", False)
        new = not current
        self.set("autobio", new)

        if new:
            await utils.answer(message, self.strings["autobio_enabled"])
            self.autobio.start()
        else:
            await utils.answer(message, self.strings["autobio_disabled"])
            self.autobio.stop()

    @authorized
    @loader.command()
    async def ylike(self, message: Message, client: ClientAsync):
        """❤"""
        try:
            queues = await client.queues_list()
            last_queue = await client.queue(queues[0].id)

            last_track_id = last_queue.get_current_track()
            last_track = await last_track_id.fetch_track_async()
        except Exception:
            await utils.answer(message, self.strings["radio_error"])
            return

        liked_tracks = await client.users_likes_tracks()
        liked_tracks = await liked_tracks.fetch_tracks_async()

        if isinstance(liked_tracks, list):
            if last_track in liked_tracks:
                return await utils.answer(message, self.strings["already_liked"])

            await last_track.like_async()
            return await utils.answer(message, self.strings["liked"])

        await last_track.like_async()
        await utils.answer(message, self.strings["liked"])

    @authorized
    @loader.command()
    async def ydislike(self, message: Message, client: ClientAsync):
        """💔"""
        try:
            queues = await client.queues_list()
            last_queue = await client.queue(queues[0].id)

            last_track_id = last_queue.get_current_track()
            last_track = await last_track_id.fetch_track_async()
        except Exception:
            await utils.answer(message, self.strings["radio_error"])
            return

        liked_tracks = await (await client.users_likes_tracks()).fetch_tracks_async()

        if isinstance(liked_tracks, list):
            if last_track in liked_tracks:
                await last_track.dislike_async()
                return await utils.answer(message, self.strings["disliked"])

            return await utils.answer(message, self.strings["not_liked"])

        return await utils.answer(message, self.strings["not_liked"])

    @loader.loop(interval=30)
    async def autobio(self):
        try:
            client = await ClientAsync(self.config["token"]).init()

            queues = await client.queues_list()
            last_queue = await client.queue(queues[0].id)

            last_track_id = last_queue.get_current_track()
            last_track = await last_track_id.fetch_track_async()
        except Exception:
            return

        artists = ", ".join(last_track.artists_name())
        title = last_track.title + (
            f" ({last_track.version})" if last_track.version else ""
        )

        text = self.config["autobio_template"].format(
            artists=artists,
            title=title,
        )

        try:
            await self.client(
                UpdateProfileRequest(about=text[: 140 if self._premium else 70])
            )
        except FloodWaitError as e:
            logger.info(f"Sleeping {e.seconds}")
            await sleep(e.seconds)
            return
