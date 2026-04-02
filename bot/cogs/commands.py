import discord
from discord.ext import commands

from utils.config import get_config, save_config
from utils.permissions import admin_only, is_admin
from utils.storage import (
    set_welcome_channel_id,
    set_rules_channel_id,
    set_welcome_message,
    set_command_channel_id,
)

class CommandsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config = get_config()

    @commands.command(name="download")
    async def download(self, ctx: commands.Context):
        await ctx.author.send(f"Download: {self.config['download_link']}")
        await ctx.reply("I have sent you the download link in DM.", mention_author=False)

    @commands.command(name="version")
    async def version(self, ctx: commands.Context):
        await ctx.reply(f"Current launcher version: {self.config['launcher_version']}", mention_author=False)

    @commands.command(name="install")
    async def install(self, ctx: commands.Context):
        await ctx.author.send(f"Install video: {self.config['install_video_link']}")
        await ctx.reply("I have sent you the install video in DM.", mention_author=False)

    @commands.command(name="help")
    async def help(self, ctx: commands.Context):
        embed = discord.Embed(title="PK Launcher Bot Commands", color=discord.Color.blurple())
        embed.add_field(name="General", value="`!download`, `!version`, `!install`", inline=False)
        embed.add_field(name="Utility", value="`!ping`, `!uptime`, `!userinfo`, `!serverinfo`, `!avatar`, `!members`", inline=False)
        embed.add_field(name="Community", value="`!afk`, `!profile`, `!daily`, `!balance`, `!countdown`, `!shop`, `!buy`, `!inventory`", inline=False)
        embed.add_field(name="AI", value="`!ai`, `!ask`, `!summarize`, `!rewrite`, `!ailangshow`", inline=False)
        embed.add_field(name="Music", value="`!join`, `!play`, `!controls`, `!pause`, `!resume`, `!skip`, `!stop`, `!queue`, `!now`, `!volume`", inline=False)
        embed.add_field(name="Levels", value="`!rank`, `!leaderboard`", inline=False)
        embed.add_field(name="Invites", value="`!invites`, `!invite @user`, `!invited`, `!invited @user`", inline=False)
        embed.add_field(name="Feedback", value="`!report <problem>`, `!review <stars> <text>`, `!reviewtop`", inline=False)
        embed.add_field(name="Suggestions", value="`!suggest <text>`", inline=False)

        if is_admin(ctx.author):
            embed.add_field(name="Tickets", value="`!ticketsetup`, `!ticketpanel`, `!ticketclose`", inline=False)
            embed.add_field(name="Onboarding", value="`!setwelcome #channel`, `!setrules #channel`, `!setwelcomemsg <text>`, `!setvip @role`", inline=False)
            embed.add_field(name="Shop Admin", value="`!setshoprole <item_id> @role`", inline=False)
            embed.add_field(name="AI Admin", value="`!teach <q> | <a>`, `!forget <q>`, `!ailang <urdu|roman|english>`", inline=False)
            embed.add_field(name="AI Moderation", value="`!aimod on/off`, `!setaimod #channel`", inline=False)
            embed.add_field(name="AI Auto", value="`!aiauto on/off`, `!setaiautoignore #channel`", inline=False)
            embed.add_field(name="Suggestions Admin", value="`!setsuggest #channel`", inline=False)
            embed.add_field(name="Feedback Admin", value="`!setreports #channel`, `!setreviews #channel`", inline=False)
            embed.add_field(name="Commands Channel", value="`!setcommands #channel`", inline=False)
            embed.add_field(name="Giveaways", value="`!gstart 10m 1 Prize`, `!gend <message_id>`, `!greroll <message_id>`", inline=False)
            embed.add_field(
                name="Moderation",
                value="`!kick`, `!ban`, `!unban`, `!timeout`, `!untimeout`, `!purge`, `!warn`, `!tatti`, `!addbad`, `!removebad`",
                inline=False,
            )

        await ctx.reply(embed=embed, mention_author=False)

    @commands.command(name="setwelcome")
    @commands.guild_only()
    @admin_only()
    async def setwelcome(self, ctx: commands.Context, channel: discord.TextChannel):
        await set_welcome_channel_id(ctx.guild.id, channel.id)
        await ctx.reply(f"Welcome channel set to {channel.mention}.", mention_author=False)

    @commands.command(name="setrules")
    @commands.guild_only()
    @admin_only()
    async def setrules(self, ctx: commands.Context, channel: discord.TextChannel):
        await set_rules_channel_id(ctx.guild.id, channel.id)
        await ctx.reply(f"Rules channel set to {channel.mention}.", mention_author=False)

    @commands.command(name="setwelcomemsg")
    @commands.guild_only()
    @admin_only()
    async def setwelcomemsg(self, ctx: commands.Context, *, text: str):
        await set_welcome_message(ctx.guild.id, text)
        await ctx.reply("Welcome message updated.", mention_author=False)

    @commands.command(name="setcommands")
    @commands.guild_only()
    @admin_only()
    async def setcommands(self, ctx: commands.Context, channel: discord.TextChannel):
        await set_command_channel_id(ctx.guild.id, channel.id)
        await ctx.reply(f"Commands channel set to {channel.mention}.", mention_author=False)

    @commands.command(name="setvip")
    @commands.guild_only()
    @admin_only()
    async def setvip(self, ctx: commands.Context, role: discord.Role):
        self.config["vip_role_id"] = role.id
        self.config["vip_role_name"] = role.name
        try:
            save_config()
        except Exception:
            await ctx.reply("VIP role set in memory, but failed to save config.", mention_author=False)
            return
        await ctx.reply(f"VIP role set to {role.mention}.", mention_author=False)

async def setup(bot: commands.Bot):
    await bot.add_cog(CommandsCog(bot))
