import time
import asyncio
from datetime import timedelta

import discord
from discord.ext import commands

from utils.config import get_config, save_config
from utils.permissions import admin_only
from utils.storage import add_warning, get_warning_count


class ModerationCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config = get_config()

    async def _dm_user(self, member: discord.Member, message: str):
        if not self.config.get("moderation", {}).get("dm_on_action", True):
            return
        try:
            await member.send(message)
        except Exception:
            pass

    @commands.command(name="kick")
    @admin_only()
    async def kick(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        await self._dm_user(member, f"You were kicked from {ctx.guild} for: {reason}")
        await member.kick(reason=reason)
        await ctx.reply(f"Kicked {member.mention}.", mention_author=False)

    @commands.command(name="ban")
    @admin_only()
    async def ban(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        await self._dm_user(member, f"You were banned from {ctx.guild} for: {reason}")
        await member.ban(reason=reason, delete_message_days=0)
        await ctx.reply(f"Banned {member.mention}.", mention_author=False)

    @commands.command(name="unban")
    @admin_only()
    async def unban(self, ctx: commands.Context, user_id: int):
        user = await self.bot.fetch_user(user_id)
        await ctx.guild.unban(user)
        await ctx.reply(f"Unbanned {user}.", mention_author=False)

    @commands.command(name="timeout")
    @admin_only()
    async def timeout(self, ctx: commands.Context, member: discord.Member, minutes: int, *, reason: str = "No reason provided"):
        duration = timedelta(minutes=minutes)
        await self._dm_user(member, f"You were timed out in {ctx.guild} for {minutes} minutes. Reason: {reason}")
        await member.timeout(duration, reason=reason)
        await ctx.reply(f"Timed out {member.mention} for {minutes} minutes.", mention_author=False)

    @commands.command(name="untimeout")
    @admin_only()
    async def untimeout(self, ctx: commands.Context, member: discord.Member):
        await member.timeout(None)
        await ctx.reply(f"Timeout removed for {member.mention}.", mention_author=False)

    @commands.command(name="purge")
    @admin_only()
    async def purge(self, ctx: commands.Context, amount: int):
        if amount < 1 or amount > 200:
            await ctx.reply("Amount must be between 1 and 200.", mention_author=False)
            return
        deleted = await ctx.channel.purge(limit=amount + 1)
        await ctx.send(f"Deleted {len(deleted) - 1} messages.", delete_after=5)

    @commands.command(name="warn")
    @admin_only()
    async def warn(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        await add_warning(ctx.guild.id, member.id, ctx.author.id, reason, int(time.time()))
        await self._dm_user(member, f"You were warned in {ctx.guild} for: {reason}")
        total = await get_warning_count(ctx.guild.id, member.id)
        await ctx.reply(f"Warned {member.mention}. Total warnings: {total}.", mention_author=False)

    @commands.command(name="addbad")
    @admin_only()
    async def addbad(self, ctx: commands.Context, *, words: str):
        raw_items = [w.strip().lower() for w in words.split(",")]
        items = [w for w in raw_items if w]
        if not items:
            await ctx.reply("Provide at least one word.", mention_author=False)
            return

        bad_words = self.config["auto_mod"]["bad_words"]
        added = []
        for word in items:
            if word not in bad_words:
                bad_words.append(word)
                added.append(word)

        if added:
            try:
                save_config()
            except Exception:
                await ctx.reply("Added in memory, but failed to save config (check file permissions).", mention_author=False)
                return
            await ctx.reply(f"Added: {', '.join(added)}", mention_author=False)
        else:
            await ctx.reply("All provided words already exist.", mention_author=False)

    @commands.command(name="removebad", aliases=["delbad", "badremove"])
    @admin_only()
    async def removebad(self, ctx: commands.Context, *, words: str):
        raw_items = [w.strip().lower() for w in words.split(",")]
        items = [w for w in raw_items if w]
        if not items:
            await ctx.reply("Provide at least one word.", mention_author=False)
            return

        bad_words = self.config["auto_mod"]["bad_words"]
        removed = []
        for word in items:
            if word in bad_words:
                bad_words.remove(word)
                removed.append(word)

        if removed:
            try:
                save_config()
            except Exception:
                await ctx.reply("Removed in memory, but failed to save config (check file permissions).", mention_author=False)
                return
            await ctx.reply(f"Removed: {', '.join(removed)}", mention_author=False)
        else:
            await ctx.reply("No matching words found.", mention_author=False)

    @commands.command(name="tatti")
    @admin_only()
    async def tatti(self, ctx: commands.Context, count: int, member: discord.Member):
        if count < 1:
            await ctx.reply("Count must be at least 1.", mention_author=False)
            return
        if count > 1000:
            await ctx.reply("Count too high. Max 1000.", mention_author=False)
            return

        try:
            await ctx.message.delete()
        except Exception:
            pass

        try:
            dm = await member.create_dm()
            for _ in range(count):
                await dm.send(" eat it now💩")
                await asyncio.sleep(5)
            try:
                await ctx.author.send(f"Sent {count} 💩 to {member}.")
            except Exception:
                pass
        except Exception:
            await ctx.reply("Could not DM that user.", mention_author=False)


async def setup(bot: commands.Bot):
    await bot.add_cog(ModerationCog(bot))
