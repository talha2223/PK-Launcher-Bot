import random
import time

import discord
from discord.ext import commands

from utils.config import get_config
from utils.storage import get_balance, get_economy, set_economy


class EconomyCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config = get_config()

    def _cfg(self):
        return self.config.get("economy", {})

    @commands.command(name="daily")
    @commands.guild_only()
    async def daily(self, ctx: commands.Context):
        cfg = self._cfg()
        min_reward = int(cfg.get("daily_min", 50))
        max_reward = int(cfg.get("daily_max", 120))
        streak_bonus = int(cfg.get("streak_bonus", 5))
        cooldown = int(cfg.get("daily_cooldown_seconds", 86400))

        now = int(time.time())
        data = await get_economy(ctx.guild.id, ctx.author.id)
        coins = data["coins"]
        streak = data["streak"]
        last_claim = data["last_claim"]

        if last_claim and now - last_claim < cooldown:
            next_ts = last_claim + cooldown
            await ctx.reply(f"You already claimed today. Next claim <t:{next_ts}:R>.", mention_author=False)
            return

        if last_claim and now - last_claim <= cooldown * 2:
            streak += 1
        else:
            streak = 1

        reward = random.randint(min_reward, max_reward) + max(0, streak - 1) * streak_bonus
        coins += reward

        await set_economy(ctx.guild.id, ctx.author.id, coins, streak, now)

        embed = discord.Embed(title="Daily Reward", color=discord.Color.green())
        embed.add_field(name="Reward", value=f"{reward} coins", inline=True)
        embed.add_field(name="Streak", value=str(streak), inline=True)
        embed.add_field(name="Balance", value=f"{coins} coins", inline=True)
        await ctx.reply(embed=embed, mention_author=False)

    @commands.command(name="balance", aliases=["bal", "coins"])
    @commands.guild_only()
    async def balance(self, ctx: commands.Context, member: discord.Member | None = None):
        member = member or ctx.author
        coins = await get_balance(ctx.guild.id, member.id)
        await ctx.reply(f"{member.display_name} has `{coins}` coins.", mention_author=False)


async def setup(bot: commands.Bot):
    await bot.add_cog(EconomyCog(bot))
