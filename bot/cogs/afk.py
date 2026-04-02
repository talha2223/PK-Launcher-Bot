import time

import discord
from discord.ext import commands


class AfkCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.afk = {}

    @commands.command(name="afk")
    @commands.guild_only()
    async def afk(self, ctx: commands.Context, *, reason: str = "AFK"):
        self.afk[(ctx.guild.id, ctx.author.id)] = {
            "reason": reason,
            "since": int(time.time()),
        }
        await ctx.reply(f"You are now AFK: {reason}", mention_author=False)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        author_key = (message.guild.id, message.author.id)
        if author_key in self.afk:
            self.afk.pop(author_key, None)
            await message.reply("Welcome back! AFK removed.", mention_author=False)

        if not message.mentions:
            return

        lines = []
        for member in message.mentions[:3]:
            if member.bot:
                continue
            info = self.afk.get((message.guild.id, member.id))
            if info:
                since = info["since"]
                reason = info["reason"]
                lines.append(f"{member.display_name} is AFK: {reason} • <t:{since}:R>")

        if lines:
            await message.reply("\n".join(lines), mention_author=False)


async def setup(bot: commands.Bot):
    await bot.add_cog(AfkCog(bot))
