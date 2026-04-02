import asyncio
import json
import time
from collections import defaultdict

import discord
from discord.ext import commands

from utils.ai_client import AIClient
from utils.config import get_config, save_config
from utils.permissions import admin_only


SEVERITY_ORDER = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}


class AiModerationCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config = get_config()
        self.client = AIClient(self.config)
        self.user_last = defaultdict(lambda: 0.0)
        self.semaphore = asyncio.Semaphore(2)

    def _cfg(self):
        return self.config.get("ai_moderation", {})

    def _enabled(self) -> bool:
        return bool(self._cfg().get("enabled", False))

    def _min_severity(self) -> int:
        name = str(self._cfg().get("min_severity", "medium")).lower()
        return SEVERITY_ORDER.get(name, 2)

    def _ignore_channels(self) -> set[int]:
        return set(self._cfg().get("ignore_channel_ids", []))

    def _ignore_roles(self) -> set[int]:
        return set(self._cfg().get("ignore_role_ids", []))

    def _max_chars(self) -> int:
        return int(self._cfg().get("max_chars", 600))

    def _cooldown(self) -> int:
        return int(self._cfg().get("cooldown_seconds", 12))

    def _action(self) -> str:
        return str(self._cfg().get("action", "flag")).lower()

    def _log_channel_id(self) -> int:
        return int(self._cfg().get("log_channel_id", 0))

    def _should_scan(self, message: discord.Message) -> bool:
        if not message.guild or message.author.bot:
            return False
        if not self._enabled():
            return False
        if message.channel.id in self._ignore_channels():
            return False
        if any(role.id in self._ignore_roles() for role in message.author.roles):
            return False
        if message.content.strip().startswith(self.config.get("prefix", "!")):
            return False
        return True

    async def _log_flag(self, message: discord.Message, result: dict):
        channel_id = self._log_channel_id()
        if not channel_id:
            return
        channel = message.guild.get_channel(channel_id)
        if not channel:
            return

        severity = result.get("severity", "unknown")
        categories = ", ".join(result.get("categories", [])) or "unknown"
        reason = result.get("reason", "No reason provided")

        embed = discord.Embed(title="AI Moderation Flag", color=discord.Color.orange())
        embed.add_field(name="User", value=f"{message.author} ({message.author.id})", inline=False)
        embed.add_field(name="Channel", value=message.channel.mention, inline=False)
        embed.add_field(name="Severity", value=str(severity), inline=True)
        embed.add_field(name="Categories", value=categories, inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        if message.content:
            content = message.content[:1000]
            embed.add_field(name="Message", value=content, inline=False)
        embed.add_field(name="Jump", value=f"[Go to message]({message.jump_url})", inline=False)
        await channel.send(embed=embed)

    def _parse_response(self, text: str) -> dict | None:
        text = text.strip()
        if not text:
            return None
        try:
            return json.loads(text)
        except Exception:
            pass
        # Try to extract JSON from markdown/code
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except Exception:
                return None
        return None

    async def _classify(self, content: str) -> dict | None:
        system_prompt = (
            "You are a moderation classifier. Respond with ONLY valid JSON. "
            "Return: {\"flag\":true|false, \"severity\":\"low|medium|high|critical\", "
            "\"categories\":[...], \"reason\":\"short\"}. "
            "Flag for harassment, hate, threats, sexual content, self-harm, spam, phishing, malware, doxxing."
        )
        prompt = f"Classify this message:\n\n{content}"
        try:
            response = await self.client.call(prompt, system_prompt=system_prompt)
        except Exception:
            return None
        return self._parse_response(response)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not self._should_scan(message):
            return

        now = time.time()
        if now - self.user_last[message.author.id] < self._cooldown():
            return
        self.user_last[message.author.id] = now

        content = message.content.strip()
        if not content:
            return
        content = content[: self._max_chars()]

        async with self.semaphore:
            result = await self._classify(content)

        if not result:
            return

        flag = bool(result.get("flag", False))
        severity = str(result.get("severity", "low")).lower()
        severity_rank = SEVERITY_ORDER.get(severity, 1)
        if not flag or severity_rank < self._min_severity():
            return

        await self._log_flag(message, result)

        action = self._action()
        if action == "delete":
            try:
                await message.delete()
            except Exception:
                pass

    @commands.command(name="setaimod")
    @commands.guild_only()
    @admin_only()
    async def setaimod(self, ctx: commands.Context, channel: discord.TextChannel):
        self.config.setdefault("ai_moderation", {})["log_channel_id"] = channel.id
        try:
            save_config()
        except Exception:
            await ctx.reply("Saved in memory, but failed to write config.", mention_author=False)
            return
        await ctx.reply(f"AI moderation log channel set to {channel.mention}.", mention_author=False)

    @commands.command(name="aimod")
    @commands.guild_only()
    @admin_only()
    async def aimod(self, ctx: commands.Context, mode: str):
        mode = mode.lower()
        if mode not in ("on", "off"):
            await ctx.reply("Use: !aimod on/off", mention_author=False)
            return
        self.config.setdefault("ai_moderation", {})["enabled"] = (mode == "on")
        try:
            save_config()
        except Exception:
            await ctx.reply("Saved in memory, but failed to write config.", mention_author=False)
            return
        await ctx.reply(f"AI moderation is now {mode}.", mention_author=False)

    def cog_unload(self):
        asyncio.create_task(self.client.close())


async def setup(bot: commands.Bot):
    await bot.add_cog(AiModerationCog(bot))
