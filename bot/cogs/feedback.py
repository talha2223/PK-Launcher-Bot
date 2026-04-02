import time

import discord
from discord.ext import commands

from utils.config import get_config
from utils.permissions import admin_only
from utils.storage import (
    add_review,
    get_report_channel_id,
    get_review_leaderboard,
    get_review_channel_id,
    set_report_channel_id,
    set_review_channel_id,
)


def _parse_stars(value: str) -> int:
    raw = value.strip()
    if raw.isdigit():
        count = int(raw)
    else:
        compact = raw.replace(" ", "")
        if compact and all(ch in ("⭐", "🌟") for ch in compact):
            count = len(compact)
        else:
            return 0
    return count if 1 <= count <= 5 else 0


class FeedbackCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config = get_config()

    @commands.command(name="setreports", aliases=["setreport", "setreportchannel"])
    @commands.guild_only()
    @admin_only()
    async def setreports(self, ctx: commands.Context, channel: discord.TextChannel):
        await set_report_channel_id(ctx.guild.id, channel.id)
        await ctx.reply(f"Reports channel set to {channel.mention}.", mention_author=False)

    @commands.command(name="report")
    @commands.guild_only()
    async def report(self, ctx: commands.Context, *, text: str):
        channel_id = await get_report_channel_id(ctx.guild.id)
        channel_id = channel_id or self.config.get("report_channel_id", 0)
        channel = ctx.guild.get_channel(channel_id) if channel_id else None
        if not channel:
            await ctx.reply("Report channel not configured.", mention_author=False)
            return

        embed = discord.Embed(title="New Report", description=text, color=discord.Color.orange())
        embed.set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)
        embed.set_footer(text=f"User ID: {ctx.author.id}")
        await channel.send(embed=embed)
        await ctx.reply("Report submitted.", mention_author=False)

    @commands.command(name="setreviews", aliases=["setreview", "setreviewchannel"])
    @commands.guild_only()
    @admin_only()
    async def setreviews(self, ctx: commands.Context, channel: discord.TextChannel):
        await set_review_channel_id(ctx.guild.id, channel.id)
        await ctx.reply(f"Reviews channel set to {channel.mention}.", mention_author=False)

    @commands.command(name="review")
    @commands.guild_only()
    async def review(self, ctx: commands.Context, stars: str, *, text: str):
        count = _parse_stars(stars)
        if count == 0:
            raise commands.BadArgument("Stars must be 1-5")

        channel_id = await get_review_channel_id(ctx.guild.id)
        channel_id = channel_id or self.config.get("review_channel_id", 0)
        channel = ctx.guild.get_channel(channel_id) if channel_id else None
        if not channel:
            await ctx.reply("Review channel not configured.", mention_author=False)
            return

        star_text = "⭐" * count
        embed = discord.Embed(title="Launcher Review", description=text, color=discord.Color.gold())
        embed.add_field(name="Rating", value=star_text, inline=False)
        embed.set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)
        embed.set_footer(text=f"User ID: {ctx.author.id}")
        await channel.send(embed=embed)
        await add_review(ctx.guild.id, ctx.author.id, count, text, int(time.time()))
        await ctx.reply("Review submitted. Thanks!", mention_author=False)

    @commands.command(name="reviewtop", aliases=["reviewleaderboard", "reviewlb"])
    @commands.guild_only()
    async def reviewtop(self, ctx: commands.Context, days: int = 7):
        days = max(1, min(days, 30))
        since_ts = int(time.time() - days * 86400)
        rows = await get_review_leaderboard(ctx.guild.id, since_ts, limit=10)
        if not rows:
            await ctx.reply("No reviews yet for the leaderboard.", mention_author=False)
            return

        lines = []
        for idx, (user_id, avg_stars, total) in enumerate(rows, start=1):
            member = ctx.guild.get_member(user_id)
            name = member.display_name if member else f"User {user_id}"
            avg_value = f"{float(avg_stars):.2f}"
            lines.append(f"{idx}. {name} — ⭐ {avg_value} ({int(total)} reviews)")

        embed = discord.Embed(
            title=f"Top Reviews (last {days} days)",
            description="\n".join(lines),
            color=discord.Color.blurple(),
        )
        await ctx.reply(embed=embed, mention_author=False)


async def setup(bot: commands.Bot):
    await bot.add_cog(FeedbackCog(bot))
