import re
import time
from collections import defaultdict, deque

import discord
from discord.ext import commands

from utils.config import get_config

class AutoMod(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config = get_config()
        self.link_regex = re.compile(r"https?://")
        self.invite_regex = re.compile(r"(discord\.gg/|discord\.com/invite/)", re.IGNORECASE)
        self.user_links = defaultdict(lambda: deque())
        self.join_times = deque()

    async def _warn_user(self, message: discord.Message, text: str):
        try:
            await message.channel.send(text, delete_after=5)
        except Exception:
            pass

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        content = message.content.lower()
        for bad in self.config["auto_mod"]["bad_words"]:
            if bad in content:
                await message.delete()
                await self._warn_user(message, "Please avoid inappropriate language.")
                return

        if self.config["auto_mod"].get("block_invites", False):
            if self.invite_regex.search(message.content):
                await message.delete()
                await self._warn_user(message, "Invite links are not allowed.")
                return

        link_settings = self.config["auto_mod"]["link_spam"]
        if link_settings["enabled"]:
            if self.link_regex.search(message.content):
                now = time.time()
                q = self.user_links[message.author.id]
                q.append(now)
                while q and now - q[0] > link_settings["per_seconds"]:
                    q.popleft()
                if len(q) > link_settings["max_links"]:
                    await message.delete()
                    await self._warn_user(message, "Link spam is not allowed.")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        anti_raid = self.config["auto_mod"]["anti_raid"]
        if not anti_raid["enabled"]:
            return

        now = time.time()
        self.join_times.append(now)
        while self.join_times and now - self.join_times[0] > anti_raid["per_seconds"]:
            self.join_times.popleft()

        if len(self.join_times) >= anti_raid["join_threshold"]:
            channel = member.guild.system_channel
            if channel:
                await channel.send("Possible raid detected: high join rate.")

async def setup(bot: commands.Bot):
    await bot.add_cog(AutoMod(bot))
