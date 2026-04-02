import discord
from discord.ext import commands

from utils.config import get_config
from utils.storage import get_welcome_channel_id

class WelcomeEvents(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config = get_config()

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        auto_role_id = self.config.get("auto_role_id", 0)
        auto_role_name = (self.config.get("auto_role_name") or "").strip()
        role = None
        if auto_role_id:
            role = member.guild.get_role(auto_role_id)
        if role is None and auto_role_name:
            role = discord.utils.get(member.guild.roles, name=auto_role_name)
        if role:
            try:
                await member.add_roles(role, reason="Auto role on join")
            except discord.Forbidden:
                pass

        vip_role_id = self.config.get("vip_role_id", 0)
        vip_role_name = (self.config.get("vip_role_name") or "").strip()
        vip_role = None
        if vip_role_id:
            vip_role = member.guild.get_role(vip_role_id)
        if vip_role is None and vip_role_name:
            vip_role = discord.utils.get(member.guild.roles, name=vip_role_name)
        if vip_role:
            try:
                await member.add_roles(vip_role, reason="Auto VIP role on join")
            except discord.Forbidden:
                pass

        welcome_channel_id = await get_welcome_channel_id(member.guild.id)
        channel_id = welcome_channel_id or self.config["welcome_channel_id"]
        channel = member.guild.get_channel(channel_id)
        rules_channel = member.guild.get_channel(self.config["rules_channel_id"])
        if not channel:
            return

        rules_text = rules_channel.mention if rules_channel else "the rules channel"
        template = self.config.get(
            "welcome_message",
            "Welcome {user}! Please read {rules}.PK Launcher info: use !download to get the latest build.",
        )
        msg = template.format(user=member.display_name, server=member.guild.name, rules=rules_text)
        await channel.send(msg)

async def setup(bot: commands.Bot):
    await bot.add_cog(WelcomeEvents(bot))
