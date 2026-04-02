import asyncio
import time

import discord
from discord.ext import commands

from utils.storage import add_invite_record, get_invite_stats, get_invited_list, mark_invite_left


class InvitesCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cache: dict[int, dict[str, int]] = {}
        self._primed = False

    async def _prime_cache(self):
        for guild in self.bot.guilds:
            await self._refresh_guild_cache(guild)

    async def _refresh_guild_cache(self, guild: discord.Guild):
        me = guild.me
        if not me or not me.guild_permissions.manage_guild:
            return
        try:
            invites = await guild.invites()
        except Exception:
            return
        self.cache[guild.id] = {i.code: i.uses for i in invites}

    @commands.Cog.listener()
    async def on_ready(self):
        if self._primed:
            return
        self._primed = True
        await self._prime_cache()

    @commands.Cog.listener()
    async def on_invite_create(self, invite: discord.Invite):
        if invite.guild is None:
            return
        guild_cache = self.cache.get(invite.guild.id, {})
        guild_cache[invite.code] = invite.uses or 0
        self.cache[invite.guild.id] = guild_cache

    @commands.Cog.listener()
    async def on_invite_delete(self, invite: discord.Invite):
        if invite.guild is None:
            return
        guild_cache = self.cache.get(invite.guild.id, {})
        if invite.code in guild_cache:
            guild_cache.pop(invite.code, None)
        self.cache[invite.guild.id] = guild_cache

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = member.guild
        me = guild.me
        if not me or not me.guild_permissions.manage_guild:
            return

        try:
            invites = await guild.invites()
        except Exception:
            return

        old = self.cache.get(guild.id, {})
        used = None
        for inv in invites:
            old_uses = old.get(inv.code, 0)
            if (inv.uses or 0) > old_uses:
                used = inv
                break

        self.cache[guild.id] = {i.code: i.uses for i in invites}

        if used and used.inviter:
            await add_invite_record(
                guild_id=guild.id,
                inviter_id=used.inviter.id,
                invited_id=member.id,
                invite_code=used.code,
                joined_at=int(time.time()),
            )

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        await mark_invite_left(member.guild.id, member.id, int(time.time()))

    @commands.command(name="invites")
    @commands.guild_only()
    async def invites(self, ctx: commands.Context, member: discord.Member | None = None):
        member = member or ctx.author
        total, left = await get_invite_stats(ctx.guild.id, member.id)
        net = total - left
        embed = discord.Embed(title="Invites", color=discord.Color.green())
        embed.add_field(name="User", value=f"{member} ({member.id})", inline=False)
        embed.add_field(name="Total Invites", value=str(total), inline=True)
        embed.add_field(name="Left", value=str(left), inline=True)
        embed.add_field(name="Net", value=str(net), inline=True)
        await ctx.reply(embed=embed, mention_author=False)

    @commands.command(name="invite")
    @commands.guild_only()
    async def invite(self, ctx: commands.Context, member: discord.Member):
        await self.invites(ctx, member)

    @commands.command(name="invited")
    @commands.guild_only()
    async def invited(self, ctx: commands.Context, member: discord.Member | None = None):
        member = member or ctx.author
        rows = await get_invited_list(ctx.guild.id, member.id, limit=10)
        if not rows:
            await ctx.reply("No invited members found.", mention_author=False)
            return

        lines = []
        for invited_id, joined_at, left_at, code in rows:
            user = ctx.guild.get_member(invited_id)
            name = user.display_name if user else f"User {invited_id}"
            status = "left" if left_at else "active"
            when = f"<t:{joined_at}:R>" if joined_at else "unknown"
            lines.append(f"- {name} ({status}) • {when} • `{code}`")

        embed = discord.Embed(title=f"Invited By {member.display_name}", description="\n".join(lines))
        await ctx.reply(embed=embed, mention_author=False)


async def setup(bot: commands.Bot):
    await bot.add_cog(InvitesCog(bot))
