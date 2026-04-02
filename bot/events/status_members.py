import logging

import discord
from discord.ext import commands

from utils.config import get_config


class StatusMembers(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config = get_config()

    def _enabled_for(self, guild: discord.Guild) -> bool:
        if not self.config.get("status_use_member_count", False):
            return False
        guild_id = int(self.config.get("guild_id", 0))
        return (guild_id == 0) or (guild_id == guild.id)

    async def _update(self, guild: discord.Guild):
        if not self._enabled_for(guild):
            return
        try:
            count = guild.member_count or len(guild.members)
            self.bot.shared_state.users = count
            await self.bot.activity_manager.update_status()
        except Exception:
            logging.exception("Failed to update status from member count")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        await self._update(member.guild)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        await self._update(member.guild)


async def setup(bot: commands.Bot):
    await bot.add_cog(StatusMembers(bot))
