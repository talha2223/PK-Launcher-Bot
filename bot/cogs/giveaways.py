import asyncio
import random
import time
from datetime import datetime, timezone

import discord
from discord.ext import commands

from utils.permissions import admin_only
from utils.storage import (
    add_giveaway,
    get_active_giveaways,
    get_giveaway,
    mark_giveaway_ended,
)


GIVEAWAY_REACTION = "🎉"


def parse_duration(text: str) -> int:
    text = text.strip().lower()
    if text.endswith("s"):
        return int(text[:-1])
    if text.endswith("m"):
        return int(text[:-1]) * 60
    if text.endswith("h"):
        return int(text[:-1]) * 3600
    if text.endswith("d"):
        return int(text[:-1]) * 86400
    # default minutes
    return int(text) * 60


class GiveawaysCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        asyncio.create_task(self._restore_giveaways())

    async def _restore_giveaways(self):
        await self.bot.wait_until_ready()
        giveaways = await get_active_giveaways()
        for g in giveaways:
            delay = max(1, int(g["end_at"] - time.time()))
            asyncio.create_task(self._end_giveaway_after(delay, g["channel_id"], g["message_id"], g["winners"]))

    async def _end_giveaway_after(self, delay: int, channel_id: int, message_id: int, winners: int):
        await asyncio.sleep(delay)
        await self._end_giveaway(channel_id, message_id, winners)

    async def _end_giveaway(self, channel_id: int, message_id: int, winners: int):
        channel = self.bot.get_channel(channel_id)
        if not channel:
            await mark_giveaway_ended(message_id)
            return

        try:
            msg = await channel.fetch_message(message_id)
        except Exception:
            await mark_giveaway_ended(message_id)
            return

        reaction = discord.utils.get(msg.reactions, emoji=GIVEAWAY_REACTION)
        if not reaction:
            await mark_giveaway_ended(message_id)
            await channel.send("Giveaway ended. No entries.")
            return

        users = []
        async for user in reaction.users():
            if not user.bot:
                users.append(user)

        if not users:
            await mark_giveaway_ended(message_id)
            await channel.send("Giveaway ended. No valid entries.")
            return

        winners = min(winners, len(users))
        chosen = random.sample(users, winners)
        winner_mentions = ", ".join(u.mention for u in chosen)

        # update embed
        embed = msg.embeds[0] if msg.embeds else discord.Embed(title="Giveaway")
        embed.color = discord.Color.red()
        embed.add_field(name="Status", value="Ended", inline=False)
        embed.add_field(name="Winners", value=winner_mentions, inline=False)
        await msg.edit(embed=embed)

        await channel.send(f"Congratulations {winner_mentions}! You won the giveaway!")
        await mark_giveaway_ended(message_id)

    @commands.command(name="gstart", aliases=["giveawaystart"])
    @commands.guild_only()
    @admin_only()
    async def gstart(self, ctx: commands.Context, duration: str, winners: int, *, prize: str):
        try:
            seconds = parse_duration(duration)
        except Exception:
            await ctx.reply("Invalid duration. Example: 10m, 2h, 1d", mention_author=False)
            return

        if winners < 1:
            await ctx.reply("Winners must be at least 1.", mention_author=False)
            return

        end_at = int(time.time() + seconds)
        end_text = f"<t:{end_at}:R>"

        embed = discord.Embed(title="🎉 Giveaway 🎉", color=discord.Color.green())
        embed.add_field(name="Prize", value=prize, inline=False)
        embed.add_field(name="Winners", value=str(winners), inline=True)
        embed.add_field(name="Ends", value=end_text, inline=True)
        embed.set_footer(text=f"Hosted by {ctx.author}")

        msg = await ctx.send(embed=embed)
        await msg.add_reaction(GIVEAWAY_REACTION)

        await add_giveaway(
            guild_id=ctx.guild.id,
            channel_id=ctx.channel.id,
            message_id=msg.id,
            prize=prize,
            winners=winners,
            end_at=end_at,
            host_id=ctx.author.id,
        )

        asyncio.create_task(self._end_giveaway_after(seconds, ctx.channel.id, msg.id, winners))

    @commands.command(name="gend", aliases=["giveawayend"])
    @commands.guild_only()
    @admin_only()
    async def gend(self, ctx: commands.Context, message_id: int):
        giveaway = await get_giveaway(message_id)
        if not giveaway:
            await ctx.reply("Giveaway not found.", mention_author=False)
            return

        await self._end_giveaway(giveaway["channel_id"], giveaway["message_id"], giveaway["winners"])

    @commands.command(name="greroll", aliases=["giveawayreroll"])
    @commands.guild_only()
    @admin_only()
    async def greroll(self, ctx: commands.Context, message_id: int):
        giveaway = await get_giveaway(message_id)
        if not giveaway:
            await ctx.reply("Giveaway not found.", mention_author=False)
            return

        channel = ctx.guild.get_channel(giveaway["channel_id"])
        if not channel:
            await ctx.reply("Channel not found.", mention_author=False)
            return

        try:
            msg = await channel.fetch_message(message_id)
        except Exception:
            await ctx.reply("Giveaway message not found.", mention_author=False)
            return

        reaction = discord.utils.get(msg.reactions, emoji=GIVEAWAY_REACTION)
        if not reaction:
            await ctx.reply("No entries found.", mention_author=False)
            return

        users = []
        async for user in reaction.users():
            if not user.bot:
                users.append(user)

        if not users:
            await ctx.reply("No valid entries.", mention_author=False)
            return

        winners = min(giveaway["winners"], len(users))
        chosen = random.sample(users, winners)
        winner_mentions = ", ".join(u.mention for u in chosen)
        await ctx.send(f"New winners: {winner_mentions}")


async def setup(bot: commands.Bot):
    await bot.add_cog(GiveawaysCog(bot))
