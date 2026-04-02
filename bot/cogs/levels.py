import asyncio
import random
import time
from pathlib import Path

import aiosqlite
import discord
from discord.ext import commands

from utils.config import get_config

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "levels.db"


def level_from_xp(xp: int) -> int:
    return int((xp / 100) ** 0.5)


def xp_for_level(level: int) -> int:
    return (level ** 2) * 100


class LevelsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config = get_config()
        self.cooldowns = {}
        self.db_lock = asyncio.Lock()

    async def _init_db(self):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "CREATE TABLE IF NOT EXISTS levels (guild_id INTEGER, user_id INTEGER, xp INTEGER, PRIMARY KEY (guild_id, user_id))"
            )
            await db.commit()

    async def cog_load(self):
        await self._init_db()

    async def add_xp(self, guild_id: int, user_id: int, amount: int):
        async with self.db_lock:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(
                    "INSERT INTO levels (guild_id, user_id, xp) VALUES (?, ?, ?) "
                    "ON CONFLICT(guild_id, user_id) DO UPDATE SET xp = xp + ?",
                    (guild_id, user_id, amount, amount),
                )
                await db.commit()

    async def get_xp(self, guild_id: int, user_id: int) -> int:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT xp FROM levels WHERE guild_id = ? AND user_id = ?",
                (guild_id, user_id),
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0

    async def top_xp(self, guild_id: int, limit: int = 10):
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT user_id, xp FROM levels WHERE guild_id = ? ORDER BY xp DESC LIMIT ?",
                (guild_id, limit),
            ) as cursor:
                return await cursor.fetchall()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        levels_cfg = self.config.get("levels", {})
        if not levels_cfg.get("enabled", True):
            return

        now = time.time()
        last = self.cooldowns.get(message.author.id, 0)
        if now - last < levels_cfg.get("cooldown_seconds", 30):
            return

        self.cooldowns[message.author.id] = now
        xp_gain = random.randint(levels_cfg.get("min_xp", 5), levels_cfg.get("max_xp", 15))
        await self.add_xp(message.guild.id, message.author.id, xp_gain)

    @commands.command(name="rank")
    async def rank(self, ctx: commands.Context, member: discord.Member | None = None):
        member = member or ctx.author
        xp = await self.get_xp(ctx.guild.id, member.id)
        level = level_from_xp(xp)
        next_level_xp = xp_for_level(level + 1)
        embed = discord.Embed(title=f"{member.display_name}'s Rank", color=discord.Color.gold())
        embed.add_field(name="Level", value=str(level), inline=True)
        embed.add_field(name="XP", value=f"{xp}/{next_level_xp}", inline=True)
        embed.set_thumbnail(url=member.display_avatar.url)
        await ctx.reply(embed=embed, mention_author=False)

    @commands.command(name="leaderboard")
    async def leaderboard(self, ctx: commands.Context):
        rows = await self.top_xp(ctx.guild.id, limit=10)
        if not rows:
            await ctx.reply("No leaderboard data yet.", mention_author=False)
            return
        lines = []
        for idx, (user_id, xp) in enumerate(rows, start=1):
            user = ctx.guild.get_member(user_id)
            name = user.display_name if user else f"User {user_id}"
            lines.append(f"{idx}. {name} — {xp} XP")
        embed = discord.Embed(title="Leaderboard", description="\n".join(lines), color=discord.Color.orange())
        await ctx.reply(embed=embed, mention_author=False)

    @commands.command(name="setxp")
    @commands.has_permissions(administrator=True)
    async def setxp(self, ctx: commands.Context, member: discord.Member, xp: int):
        if xp < 0:
            await ctx.reply("XP must be >= 0.", mention_author=False)
            return
        async with self.db_lock:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(
                    "INSERT INTO levels (guild_id, user_id, xp) VALUES (?, ?, ?) "
                    "ON CONFLICT(guild_id, user_id) DO UPDATE SET xp = ?",
                    (ctx.guild.id, member.id, xp, xp),
                )
                await db.commit()
        await ctx.reply(f"Set {member.mention}'s XP to {xp}.", mention_author=False)


async def setup(bot: commands.Bot):
    await bot.add_cog(LevelsCog(bot))
