from datetime import datetime, timezone

import discord
from discord.ext import commands

BOT_START = datetime.now(timezone.utc)


class UtilityCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="ping")
    async def ping(self, ctx: commands.Context):
        latency_ms = int(self.bot.latency * 1000)
        await ctx.reply(f"Pong! `{latency_ms}ms`", mention_author=False)

    @commands.command(name="uptime")
    async def uptime(self, ctx: commands.Context):
        now = datetime.now(timezone.utc)
        delta = now - BOT_START
        hours, rem = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(rem, 60)
        await ctx.reply(f"Uptime: `{hours}h {minutes}m {seconds}s`", mention_author=False)

    @commands.command(name="userinfo")
    async def userinfo(self, ctx: commands.Context, member: discord.Member | None = None):
        member = member or ctx.author
        embed = discord.Embed(title=f"User Info: {member}", color=discord.Color.green())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="ID", value=str(member.id), inline=True)
        embed.add_field(name="Joined", value=member.joined_at.strftime("%Y-%m-%d"), inline=True)
        embed.add_field(name="Created", value=member.created_at.strftime("%Y-%m-%d"), inline=True)
        embed.add_field(name="Roles", value=", ".join(r.mention for r in member.roles[1:]) or "None", inline=False)
        await ctx.reply(embed=embed, mention_author=False)

    @commands.command(name="serverinfo")
    async def serverinfo(self, ctx: commands.Context):
        guild = ctx.guild
        if not guild:
            return
        embed = discord.Embed(title=f"Server Info: {guild.name}", color=discord.Color.blue())
        embed.set_thumbnail(url=guild.icon.url if guild.icon else discord.Embed.Empty)
        embed.add_field(name="ID", value=str(guild.id), inline=True)
        embed.add_field(name="Members", value=str(guild.member_count), inline=True)
        embed.add_field(name="Owner", value=str(guild.owner), inline=True)
        embed.add_field(name="Created", value=guild.created_at.strftime("%Y-%m-%d"), inline=True)
        await ctx.reply(embed=embed, mention_author=False)

    @commands.command(name="members")
    @commands.guild_only()
    async def members(self, ctx: commands.Context):
        guild = ctx.guild
        if not guild:
            return
        total = guild.member_count or len(guild.members)
        humans = sum(1 for m in guild.members if not m.bot)
        bots = sum(1 for m in guild.members if m.bot)
        await ctx.reply(
            f"Members: `{total}` (Humans: `{humans}`, Bots: `{bots}`)",
            mention_author=False,
        )

    @commands.command(name="avatar")
    async def avatar(self, ctx: commands.Context, member: discord.Member | None = None):
        member = member or ctx.author
        embed = discord.Embed(title=f"{member}'s Avatar", color=discord.Color.purple())
        embed.set_image(url=member.display_avatar.url)
        await ctx.reply(embed=embed, mention_author=False)

    @commands.command(name="countdown")
    async def countdown(self, ctx: commands.Context, date: str, *, title: str = "Event"):
        try:
            target = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            await ctx.reply("Use date format: YYYY-MM-DD", mention_author=False)
            return

        now = datetime.now(timezone.utc)
        if target <= now:
            await ctx.reply(f"'{title}' has already passed.", mention_author=False)
            return

        ts = int(target.timestamp())
        delta = target - now
        days = delta.days
        hours, rem = divmod(delta.seconds, 3600)
        minutes, _ = divmod(rem, 60)

        embed = discord.Embed(title=f"Countdown: {title}", color=discord.Color.teal())
        embed.add_field(name="Date", value=f"<t:{ts}:F>", inline=False)
        embed.add_field(name="Time Left", value=f"{days}d {hours}h {minutes}m", inline=False)
        embed.add_field(name="Relative", value=f"<t:{ts}:R>", inline=False)
        await ctx.reply(embed=embed, mention_author=False)


async def setup(bot: commands.Bot):
    await bot.add_cog(UtilityCog(bot))
