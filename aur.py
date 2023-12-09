__version__ = (1, 0, 0)

#  Module for working with Arch User Repository
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

# requires: aiohttp
# meta developer: @asnct
# meta desc: Module for working with Arch User Repository

import aiohttp
from telethon.tl.types import Message

from .. import loader, utils


class AUR(loader.Module):
    """Module for working with Arch User Repository"""

    strings = {
        "name": "AUR",
        "no_args": "🚫 <b>Specify the package name to search!</b>",
        "no_results": "🚫 <b>Package not found</b>",
        "error": "🚫 <b>An error occurred during search!</b>\n\n<code>{}</code>",
        "package_info": (
            "📦 <code>{pkg_name}</code>\n"
            "ℹ️ <b>{desc}</b>\n"
            "🧑 <b>Maintainer:</b> <code>{maintainer}</code>\n"
            "🔗 {link}"
        ),
    }

    async def search(self, arg: str):
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://aur.archlinux.org/rpc/v5/search/{arg}?by=name-desc"
            ) as response:
                json = await response.json()

                if json["type"] == "error":
                    raise ValueError(json["error"])

                return json

    @loader.command()
    async def aursearch(self, message: Message):
        """<package name> - Looks for a package in the Arch User Repository"""
        args = utils.get_args_raw(message)

        if not args:
            await utils.answer(message, self.strings("no_args"))
            return

        try:
            result = await self.search(args)
        except Exception as e:
            await utils.answer(message, self.strings("error").format(e))
            return

        if result["resultcount"] == 0:
            await utils.answer(message, self.strings("no_results"))
            return

        messages = []

        for package in result["results"][:50]:
            messages += [
                self.strings("package_info").format(
                    pkg_name=package["Name"],
                    desc=package["Description"],
                    maintainer=package["Maintainer"],
                    link=f"https://aur.archlinux.org/packages/{package['Name']}",
                )
            ]

        await self.inline.list(
            message=message,
            strings=messages,
        )
