import discord
from discord.ext import commands

from utils.storage import get_command_channel_id


class CommandChannelCleaner(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.counts: dict[int, int] = {}

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        channel_id = await get_command_channel_id(message.guild.id)
        if not channel_id or message.channel.id != channel_id:
            return

        purge_count = 30
        try:
            purge_count = int(self.bot.config.get("command_channel_purge_count", 30))
        except Exception:
            purge_count = 30

        current = self.counts.get(message.guild.id, 0) + 1
        self.counts[message.guild.id] = current

        if current < purge_count:
            return

        self.counts[message.guild.id] = 0
        try:
            await message.channel.purge(limit=purge_count, check=lambda m: not m.pinned, bulk=True)
        except Exception:
            try:
                await message.channel.purge(limit=purge_count, check=lambda m: not m.pinned, bulk=False)
            except Exception:
                pass


async def setup(bot: commands.Bot):
    await bot.add_cog(CommandChannelCleaner(bot))
