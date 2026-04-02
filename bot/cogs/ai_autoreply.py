import asyncio
import os
import re
import time
from collections import defaultdict

import discord
from discord.ext import commands

from utils.ai_client import AIClient
from utils.config import get_config, save_config
from utils.permissions import admin_only


def _split_long(text: str, limit: int = 2000):
    if len(text) <= limit:
        return [text]
    chunks = []
    current = []
    size = 0
    for line in text.split("\n"):
        if size + len(line) + 1 > limit and current:
            chunks.append("\n".join(current))
            current = [line]
            size = len(line)
        else:
            current.append(line)
            size += len(line) + 1
    if current:
        chunks.append("\n".join(current))
    return chunks


class AiAutoReplyCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config = get_config()
        self.client = AIClient(self.config)
        self.user_last = defaultdict(lambda: 0.0)
        self.channel_last = defaultdict(lambda: 0.0)
        self.semaphore = asyncio.Semaphore(2)

    def _cfg(self) -> dict:
        return self.config.get("ai_auto", {})

    def _enabled(self) -> bool:
        return bool(self._cfg().get("enabled", False))

    def _min_length(self) -> int:
        return int(self._cfg().get("min_length", 6))

    def _max_chars(self) -> int:
        return int(self._cfg().get("max_chars", 500))

    def _cooldown(self) -> int:
        return int(self._cfg().get("cooldown_seconds", 45))

    def _channel_cooldown(self) -> int:
        return int(self._cfg().get("channel_cooldown_seconds", 10))

    def _ignore_channels(self) -> set[int]:
        return set(self._cfg().get("ignore_channel_ids", []))

    def _ignore_roles(self) -> set[int]:
        return set(self._cfg().get("ignore_role_ids", []))

    def _keywords(self) -> list[str]:
        return [str(k).lower() for k in self._cfg().get("keywords", [])]

    def _language_instruction(self) -> str | None:
        lang = str(self.config.get("ai", {}).get("language", "urdu")).lower()
        if lang in ("urdu", "ur"):
            return "Reply in Urdu (اردو) using native script."
        if lang in ("roman", "roman_urdu", "roman-urdu"):
            return "Reply in Roman Urdu (English letters)."
        if lang in ("english", "en"):
            return "Reply in English."
        return None

    def _has_api_key(self) -> bool:
        return any(
            os.getenv(k)
            for k in (
                "GOOGLE_API_KEY",
                "GEMINI_API_KEY",
                "GROQ_API_KEY",
                "OPENROUTER_API_KEY",
            )
        )

    async def _reply_long(self, message: discord.Message, text: str):
        for chunk in _split_long(text):
            await message.reply(chunk, mention_author=False)

    async def _is_reply_to_bot(self, message: discord.Message) -> bool:
        if not message.reference:
            return False
        resolved = message.reference.resolved
        if isinstance(resolved, discord.Message):
            return resolved.author.id == self.bot.user.id
        try:
            ref_msg = await message.channel.fetch_message(message.reference.message_id)
        except Exception:
            return False
        return ref_msg.author.id == self.bot.user.id

    def _contains_keyword(self, content: str) -> bool:
        content = content.lower()
        for kw in self._keywords():
            if kw and kw in content:
                return True
        return False

    def _should_scan(self, message: discord.Message) -> bool:
        if not message.guild or message.author.bot:
            return False
        if not self._enabled():
            return False
        if not self._has_api_key():
            return False
        if message.channel.id in self._ignore_channels():
            return False
        if any(role.id in self._ignore_roles() for role in message.author.roles):
            return False
        if message.content.strip().startswith(self.config.get("prefix", "!")):
            return False
        if len(message.content.strip()) < self._min_length():
            return False
        return True

    async def _triggered(self, message: discord.Message) -> bool:
        # RESPOND TO EVERY MESSAGE - no filters needed
        return True

    async def _generate_reply(self, message: discord.Message) -> str:
        base_prompt = self._cfg().get("system_prompt") or self.config.get("ai", {}).get("system_prompt")
        lang_hint = self._language_instruction()
        system_prompt = " ".join(p for p in (base_prompt, lang_hint) if p)
        prompt = (
            "You are a helpful PK Launcher support assistant. "
            "Reply in 1-3 short sentences. If unsure, ask a clarifying question.\n\n"
            f"User message: {message.content}"
        )
        return await self.client.call(prompt, system_prompt=system_prompt)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not self._should_scan(message):
            return
        if not await self._triggered(message):
            return

        now = time.time()
        if now - self.user_last[message.author.id] < self._cooldown():
            return
        if now - self.channel_last[message.channel.id] < self._channel_cooldown():
            return

        self.user_last[message.author.id] = now
        self.channel_last[message.channel.id] = now

        content = message.content.strip()[: self._max_chars()]
        if not content:
            return

        async with self.semaphore:
            try:
                reply = await self._generate_reply(message)
            except Exception:
                return

        if reply:
            await self._reply_long(message, reply)

    @commands.command(name="aiauto")
    @commands.guild_only()
    @admin_only()
    async def aiauto(self, ctx: commands.Context, mode: str):
        mode = mode.lower()
        if mode not in ("on", "off"):
            await ctx.reply("Use: !aiauto on/off", mention_author=False)
            return
        self.config.setdefault("ai_auto", {})["enabled"] = (mode == "on")
        try:
            save_config()
        except Exception:
            await ctx.reply("Saved in memory, but failed to write config.", mention_author=False)
            return
        await ctx.reply(f"AI auto-reply is now {mode}.", mention_author=False)

    @commands.command(name="setaiautoignore")
    @commands.guild_only()
    @admin_only()
    async def setaiautoignore(self, ctx: commands.Context, channel: discord.TextChannel):
        cfg = self.config.setdefault("ai_auto", {})
        ids = set(cfg.get("ignore_channel_ids", []))
        ids.add(channel.id)
        cfg["ignore_channel_ids"] = sorted(ids)
        try:
            save_config()
        except Exception:
            await ctx.reply("Saved in memory, but failed to write config.", mention_author=False)
            return
        await ctx.reply(f"AI auto-reply will ignore {channel.mention}.", mention_author=False)

    def cog_unload(self):
        asyncio.create_task(self.client.close())


async def setup(bot: commands.Bot):
    await bot.add_cog(AiAutoReplyCog(bot))
