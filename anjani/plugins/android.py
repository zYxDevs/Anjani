""" Android Plugin """
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

import json

from anjani import command, plugin

class Android(plugin.Plugin):

    async def cmd_magisk(self, _: command.Context) -> str:
        url = "https://raw.githubusercontent.com/topjohnwu/magisk-files/master/"
        releases = ""

        for version in {"stable", "beta", "canary"}:
            async with self.bot.http.get(url + version + ".json") as resp:
                try:
                    data = json.loads(await resp.text())
                except json.JSONDecodeError:
                    return "There was a problem with connection, try again..."

                releases += (
                    f"**{version.title()}**:\n"
                    f"• [Changelog]({data['magisk']['note']})\n"
                    f"• App - [{data['magisk']['version']} | {data['magisk']['versionCode']}]({data['magisk']['link']})\n"
                    f"• Stub - [{data['stub']['versionCode']}]({data['stub']['link']})\n\n"
                )

        return releases
