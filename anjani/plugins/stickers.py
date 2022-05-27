"""stickers commands"""
# Copyright (C) 2020 - 2022  UserbotIndo Team, <https://github.com/userbotindo.git>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import shlex
from typing import Any, ClassVar, Optional

from aiopath import AsyncPath
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser
from PIL import Image
from pyrogram import emoji, raw
from pyrogram.errors import StickersetInvalid
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from anjani import command, plugin, util


class Sticker(plugin.Plugin):
    name: ClassVar[str] = "Stickers"
    helpable: ClassVar[bool] = True

    @staticmethod
    async def resize_video(media: AsyncPath):
        metadata = extractMetadata(createParser(str(media)))
        width = round(metadata.get("width", 512))  # type: ignore
        height = round(metadata.get("height", 512))  # type: ignore
        if height == width:
            height, width = 512, 512
        elif height > width:
            height, width = 512, -1
        elif width > height:
            height, width = -1, 512

        video = AsyncPath("downloads/stickers.webm")
        arg = (
            f"ffmpeg -i {media} -ss 00:00:00 -to 00:00:03 -map 0:v -b 256k -fs 262144" + \
            f" -c:v libvpx-vp9 -vf scale={width}:{height},fps=30 {video} -y"
        )
        await util.system.run_command(*shlex.split(arg))
        await media.unlink()
        return video

    @staticmethod
    async def resize_image(image: AsyncPath):
        img = Image.open(str(image))
        scale = 512 / max(img.width, img.height)
        new_size = (int(img.width * scale), int(img.height * scale))
        img = img.resize(new_size, Image.NEAREST)
        image_path = AsyncPath("downloads/sticker.png")
        img.save(image_path, "PNG")
        await image.unlink()
        return image_path

    async def _upload_media(
        self, sticker: str
    ) -> raw.types.message_media_document.MessageMediaDocument:
        return await self.bot.client.invoke(
            raw.functions.messages.upload_media.UploadMedia(
                peer=await self.bot.client.resolve_peer("stickers"),  # type: ignore
                media=raw.types.input_media_uploaded_document.InputMediaUploadedDocument(
                    mime_type=self.bot.client.guess_mime_type(sticker) or "application/zip",
                    file=await self.bot.client.save_file(sticker),  # type: ignore
                    force_file=True,
                    thumb=None,  # type: ignore
                    attributes=[
                        raw.types.document_attribute_filename.DocumentAttributeFilename(
                            file_name=os.path.basename(sticker)
                        )
                    ],  # type: ignore
                ),
            )
        )

    async def _create_pack(
        self, author: int, pack_name: str, short_name: str, media: Any, emoji: str, set_type: str
    ):
        media = await self._upload_media(media)
        return await self.bot.client.invoke(
            raw.functions.stickers.create_sticker_set.CreateStickerSet(
                user_id=await self.bot.client.resolve_peer(author),  # type: ignore
                title=pack_name,
                short_name=short_name,
                stickers=[
                    raw.types.input_sticker_set_item.InputStickerSetItem(
                        document=raw.types.input_document.InputDocument(
                            id=media.document.id,
                            access_hash=media.document.access_hash,
                            file_reference=media.document.file_reference,
                        ),  # type: ignore
                        emoji=emoji,
                    )
                ],
                animated=set_type == "anim",
                videos=set_type == "vid",
            )
        )

    async def _add_sticker(self, short_name: str, media: Any, emoji: str):
        media = await self._upload_media(media)
        return await self.bot.client.invoke(
            raw.functions.stickers.add_sticker_to_set.AddStickerToSet(
                stickerset=raw.types.input_sticker_set_short_name.InputStickerSetShortName(
                    short_name=short_name
                ),  # type: ignore
                sticker=raw.types.input_sticker_set_item.InputStickerSetItem(
                    document=raw.types.input_document.InputDocument(
                        id=media.document.id,
                        access_hash=media.document.access_hash,
                        file_reference=media.document.file_reference,
                    ),  # type: ignore
                    emoji=emoji,
                ),
            )
        )

    async def cmd_kang(self, ctx: command.Context) -> Optional[str]:
        chat = ctx.msg.chat
        reply = ctx.msg.reply_to_message

        if not reply or not reply.media:
            return await self.text(chat.id, "sticker-no-reply")

        await ctx.respond(await self.text(chat.id, "sticker-kang-process"))
        resize = False
        anim_setpack = False
        video_setpack = False
        set_emoji = ""
        if reply.photo or reply.document and "image" in reply.document.mime_type:
            resize = True
        elif reply.document and "tgsticker" in reply.document.mime_type:
            anim_setpack = True
        elif reply.animation or (
            reply.document
            and "video" in reply.document.mime_type
            and reply.document.file_size <= 10485760
        ):
            video_setpack = True
            resize = True
        elif reply.sticker:
            if reply.sticker.file_name is None:
                return await self.text(chat.id, "sticker-filename-missing")
            if reply.sticker.emoji:
                set_emoji = reply.sticker.emoji
            video_setpack = reply.sticker.is_video
            anim_setpack = reply.sticker.is_animated
            sticker_name = reply.sticker.file_name
            if not sticker_name.endswith("tgs") or sticker_name.endswith(".webm"):
                resize = True
        else:
            return await self.text(chat.id, "sticker-unsupported-file")

        media = AsyncPath(await reply.download())
        if not media:
            return await self.text(chat.id, "sticker-media-notfound")

        packnum = 1
        emojiset = None
        if len(ctx.args) == 2:
            emojiset, packnum = ctx.args
        elif len(ctx.args) == 1:
            if ctx.input[0].isnumeric():
                packnum = ctx.args[0]
            else:
                emojiset = ctx.input[0]

        if emojiset is not None:
            setas = set_emoji
            for i in emojiset:
                if i and i in (getattr(emoji, e) for e in dir(emoji) if not e.startswith("_")):
                    set_emoji += i
                if setas and setas != set_emoji:
                    set_emoji = set_emoji[len(setas) :]
        else:
            set_emoji = "🤔"

        packnum = int(packnum)
        author = ctx.author
        if not author:  # sanity check
            return

        author_id = author.id
        author_name = author.username or author.first_name
        pack_name = f"a{author_id}_Anjani_{packnum}"
        pack_nick = f"{author_name}'s Kang Pack Vol.{packnum}"

        if resize:
            if video_setpack:
                media = await self.resize_video(media)
            else:
                media = await self.resize_image(media)
        if anim_setpack:
            pack_name += "_anim"
            pack_nick += " (Animated)"
        if video_setpack:
            pack_name += "_video"
            pack_nick += " (Video)"

        pack_name += f"_by_{self.bot.user.username}"
        exist = False
        while True:
            try:
                exist_pack = await self.bot.client.invoke(
                    raw.functions.messages.get_sticker_set.GetStickerSet(
                        stickerset=raw.types.input_sticker_set_short_name.InputStickerSetShortName(
                            short_name=pack_name,
                        ),  # type: ignore
                        hash=0,
                    )
                )
            except StickersetInvalid:
                exist = False
                break
            else:
                exist = True
                pack_limit = 50 if (anim_setpack or video_setpack) else 120
                if exist_pack.set.count >= pack_limit:
                    packnum += 1
                    pack_name = f"a{author_id}_Anjani_{packnum}"
                    pack_nick = f"{author_name}'s Kang Pack Vol.{packnum}"
                    if anim_setpack:
                        pack_name += "_anim"
                        pack_nick += " (Animated)"
                    if video_setpack:
                        pack_name += "_video"
                        pack_nick += " (Video)"
                    await ctx.respond(await self.text(chat.id, "sticker-pack-insufficent", packnum))
                    pack_name += f"_by_{self.bot.user.username}"
                    continue
                break

        if exist:
            await self._add_sticker(pack_name, str(media), set_emoji)
        else:
            set_type = "anim" if anim_setpack else "vid" if video_setpack else "static"
            await ctx.respond(await self.text(chat.id, "sticker-new-pack"))
            await self._create_pack(
                author_id, pack_nick, pack_name, str(media), set_emoji, set_type
            )

        keyb = InlineKeyboardButton(
            text=await self.text(chat.id, "sticker-pack-btn"), url=f"t.me/addstickers/{pack_name}"
        )
        await ctx.respond(
            await self.text(chat.id, "sticker-kang-success"),
            reply_markup=InlineKeyboardMarkup([[keyb]]),
        )
        await media.unlink()
