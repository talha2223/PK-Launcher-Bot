import discord
from discord.ext import commands

from utils.config import get_config


class LoggingEvents(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config = get_config()

    def _get_log_channel(self, guild: discord.Guild):
        channel_id = self.config.get("log_channel_id", 0)
        return guild.get_channel(channel_id) if channel_id else None

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        channel = self._get_log_channel(member.guild)
        if not channel:
            return
        embed = discord.Embed(title="Member Joined", color=discord.Color.green())
        embed.add_field(name="User", value=f"{member} ({member.id})", inline=False)
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        channel = self._get_log_channel(member.guild)
        if not channel:
            return
        embed = discord.Embed(title="Member Left", color=discord.Color.red())
        embed.add_field(name="User", value=f"{member} ({member.id})", inline=False)
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        channel = self._get_log_channel(message.guild)
        if not channel:
            return
        embed = discord.Embed(title="Message Deleted", color=discord.Color.orange())
        embed.add_field(name="Author", value=f"{message.author} ({message.author.id})", inline=False)
        embed.add_field(name="Channel", value=message.channel.mention, inline=False)
        embed.add_field(name="Content", value=message.content[:1000] or "[no content]", inline=False)
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot or not before.guild:
            return
        if before.content == after.content:
            return
        channel = self._get_log_channel(before.guild)
        if not channel:
            return
        embed = discord.Embed(title="Message Edited", color=discord.Color.gold())
        embed.add_field(name="Author", value=f"{before.author} ({before.author.id})", inline=False)
        embed.add_field(name="Channel", value=before.channel.mention, inline=False)
        embed.add_field(name="Before", value=before.content[:1000] or "[no content]", inline=False)
        embed.add_field(name="After", value=after.content[:1000] or "[no content]", inline=False)
        await channel.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(LoggingEvents(bot))
