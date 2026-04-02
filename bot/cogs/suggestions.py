import discord
from discord.ext import commands

from utils.config import get_config
from utils.permissions import admin_only
from utils.storage import get_suggestion_channel_id, set_suggestion_channel_id


class SuggestionsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config = get_config()

    @commands.command(name="setsuggest")
    @commands.guild_only()
    @admin_only()
    async def setsuggest(self, ctx: commands.Context, channel: discord.TextChannel):
        await set_suggestion_channel_id(ctx.guild.id, channel.id)
        await ctx.reply(f"Suggestion channel set to {channel.mention}.", mention_author=False)

    @commands.command(name="suggest")
    async def suggest(self, ctx: commands.Context, *, text: str):
        channel_id = await get_suggestion_channel_id(ctx.guild.id)
        channel_id = channel_id or self.config.get("suggestion_channel_id", 0)
        channel = ctx.guild.get_channel(channel_id) if channel_id else None
        if not channel:
            await ctx.reply("Suggestion channel not configured.", mention_author=False)
            return

        embed = discord.Embed(title="New Suggestion", description=text, color=discord.Color.teal())
        embed.set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)
        msg = await channel.send(embed=embed)
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")
        await ctx.reply("Suggestion submitted.", mention_author=False)


async def setup(bot: commands.Bot):
    await bot.add_cog(SuggestionsCog(bot))
