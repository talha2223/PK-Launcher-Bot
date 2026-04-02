import discord
from discord.ext import commands

from utils.storage import get_balance, get_economy, get_invite_stats, get_warning_count


def level_from_xp(xp: int) -> int:
    return int((xp / 100) ** 0.5)


def xp_for_level(level: int) -> int:
    return (level ** 2) * 100


class ProfileCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="profile")
    @commands.guild_only()
    async def profile(self, ctx: commands.Context, member: discord.Member | None = None):
        member = member or ctx.author

        levels_cog = self.bot.get_cog("LevelsCog")
        xp = await levels_cog.get_xp(ctx.guild.id, member.id) if levels_cog else 0
        level = level_from_xp(xp)
        next_xp = xp_for_level(level + 1)

        total_invites, left_invites = await get_invite_stats(ctx.guild.id, member.id)
        net_invites = total_invites - left_invites
        warnings = await get_warning_count(ctx.guild.id, member.id)

        econ = await get_economy(ctx.guild.id, member.id)
        coins = econ["coins"]
        streak = econ["streak"]

        embed = discord.Embed(title=f"{member.display_name}'s Profile", color=discord.Color.blurple())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Level", value=str(level), inline=True)
        embed.add_field(name="XP", value=f"{xp}/{next_xp}", inline=True)
        embed.add_field(name="Warnings", value=str(warnings), inline=True)
        embed.add_field(name="Invites", value=f"Total: {total_invites}\nLeft: {left_invites}\nNet: {net_invites}", inline=True)
        embed.add_field(name="Coins", value=str(coins), inline=True)
        embed.add_field(name="Daily Streak", value=str(streak), inline=True)
        await ctx.reply(embed=embed, mention_author=False)


async def setup(bot: commands.Bot):
    await bot.add_cog(ProfileCog(bot))
