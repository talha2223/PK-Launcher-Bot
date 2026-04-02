import discord
from discord.ext import commands

from utils.config import get_config
from utils.storage import was_greeted, mark_greeted


class Greeter(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config = get_config()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        if not self.config.get("first_message_greet_enabled", True):
            return

        if await was_greeted(message.guild.id, message.author.id):
            return

        template = self.config.get(
            "first_message_greet_text",
            "Hi {user}, welcome to {server}!",
        )
        text = template.format(user=message.author.display_name, server=message.guild.name)
        try:
            await message.channel.send(text)
        except Exception:
            return

        await mark_greeted(message.guild.id, message.author.id)


async def setup(bot: commands.Bot):
    await bot.add_cog(Greeter(bot))
