import asyncio
import re
from difflib import SequenceMatcher

import discord
from discord.ext import commands

from utils.ai_client import AIClient
from utils.config import get_config, save_config
from utils.permissions import admin_only
from utils.storage import delete_knowledge, get_knowledge, list_knowledge, upsert_knowledge


MAX_DISCORD_LEN = 2000


def _normalize_question(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def _split_long(text: str, limit: int = MAX_DISCORD_LEN):
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


def _best_match(question: str, entries: list[tuple[str, str]]):
    best_score = 0.0
    best_answer = None
    for stored_q, answer in entries:
        score = SequenceMatcher(None, question, stored_q).ratio()
        if score > best_score:
            best_score = score
            best_answer = answer
    return best_score, best_answer


class AiCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config = get_config()
        self.client = AIClient(self.config)

    def _language_instruction(self) -> str | None:
        lang = str(self.config.get("ai", {}).get("language", "urdu")).lower()
        if lang in ("urdu", "ur"):
            return "Reply in Urdu (اردو) using native script."
        if lang in ("roman", "roman_urdu", "roman-urdu"):
            return "Reply in Roman Urdu (English letters)."
        if lang in ("english", "en"):
            return "Reply in English."
        return None

    def _safe_admin_mode(self) -> bool:
        return bool(self.config.get("ai", {}).get("safe_admin", True))

    def _admin_suggest_prompt(self) -> str:
        return (
            "You are an admin assistant. You MUST NOT ping users or execute actions. "
            "Return ONLY a short, safe suggestion for which command the admin should run manually. "
            "If user asks to warn/ban/timeout/kick/ping, respond like: "
            "Use !warn @user reason (replace @user). Never mention real user IDs."
        )

    def _system_prompt(self) -> str | None:
        base = self.config.get("ai", {}).get("system_prompt")
        lang_hint = self._language_instruction()
        parts = [p for p in (base, lang_hint) if p]
        if not parts:
            return None
        return " ".join(parts)

    def _similarity_threshold(self) -> float:
        return float(self.config.get("ai", {}).get("knowledge_similarity", 0.72))

    async def _reply_long(self, ctx: commands.Context, text: str):
        for chunk in _split_long(text):
            await ctx.reply(chunk, mention_author=False)

    def _split_questions(self, text: str) -> list[str]:
        text = text.strip()
        if ";" in text:
            parts = text.split(";")
        elif "," in text:
            parts = text.split(",")
        else:
            parts = [text]
        return [p.strip() for p in parts if p.strip()]

    @commands.command(name="ai")
    @commands.guild_only()
    @commands.cooldown(2, 30, commands.BucketType.user)
    async def ai(self, ctx: commands.Context, *, prompt: str):
        system_prompt = self._system_prompt()
        if self._safe_admin_mode() and ctx.author.guild_permissions.administrator:
            system_prompt = " ".join(
                part for part in (self._admin_suggest_prompt(), self._language_instruction()) if part
            )

        try:
            response = await self.client.call(prompt, system_prompt=system_prompt)
        except Exception as exc:
            await ctx.reply(f"AI error: {exc}", mention_author=False)
            return
        await self._reply_long(ctx, response)

    @commands.command(name="summarize", aliases=["summary"])
    @commands.guild_only()
    @commands.cooldown(2, 30, commands.BucketType.user)
    async def summarize(self, ctx: commands.Context, *, text: str):
        prompt = f"Summarize this in 3-5 bullet points:\n\n{text}"
        try:
            response = await self.client.call(prompt, system_prompt=self._system_prompt())
        except Exception as exc:
            await ctx.reply(f"AI error: {exc}", mention_author=False)
            return
        await self._reply_long(ctx, response)

    @commands.command(name="rewrite")
    @commands.guild_only()
    @commands.cooldown(2, 30, commands.BucketType.user)
    async def rewrite(self, ctx: commands.Context, *, text: str):
        prompt = f"Rewrite this clearly and politely:\n\n{text}"
        try:
            response = await self.client.call(prompt, system_prompt=self._system_prompt())
        except Exception as exc:
            await ctx.reply(f"AI error: {exc}", mention_author=False)
            return
        await self._reply_long(ctx, response)

    @commands.command(name="teach")
    @commands.guild_only()
    @admin_only()
    async def teach(self, ctx: commands.Context, *, text: str):
        if "|" not in text:
            await ctx.reply("Use: !teach question | answer | optional aliases", mention_author=False)
            return
        parts = [part.strip() for part in text.split("|", 2)]
        question_part = parts[0] if len(parts) > 0 else ""
        answer = parts[1] if len(parts) > 1 else ""
        alias_part = parts[2] if len(parts) > 2 else ""
        if not question_part or not answer:
            await ctx.reply("Provide both question and answer.", mention_author=False)
            return

        questions = self._split_questions(question_part)
        aliases = self._split_questions(alias_part) if alias_part else []
        total = 0
        for q in questions + aliases:
            key = _normalize_question(q)
            if not key:
                continue
            await upsert_knowledge(ctx.guild.id, key, answer)
            total += 1

        await ctx.reply(f"Saved {total} entries. Users can now use !ask.", mention_author=False)

    @commands.command(name="forget")
    @commands.guild_only()
    @admin_only()
    async def forget(self, ctx: commands.Context, *, question: str):
        key = _normalize_question(question)
        deleted = await delete_knowledge(ctx.guild.id, key)
        if deleted:
            await ctx.reply("Deleted.", mention_author=False)
        else:
            await ctx.reply("No matching question found.", mention_author=False)

    @commands.command(name="ask")
    @commands.guild_only()
    async def ask(self, ctx: commands.Context, *, question: str):
        key = _normalize_question(question)
        answer = await get_knowledge(ctx.guild.id, key)
        if answer:
            await self._reply_long(ctx, answer)
            return

        entries = await list_knowledge(ctx.guild.id)
        if entries:
            score, best = _best_match(key, entries)
            if best and score >= self._similarity_threshold():
                await self._reply_long(ctx, best)
                return

        try:
            response = await self.client.call(question, system_prompt=self._system_prompt())
        except Exception as exc:
            await ctx.reply(f"AI error: {exc}", mention_author=False)
            return
        await self._reply_long(ctx, response)

    @commands.command(name="ailang")
    @commands.guild_only()
    @admin_only()
    async def ailang(self, ctx: commands.Context, lang: str):
        lang = lang.strip().lower()
        if lang not in ("urdu", "ur", "roman", "roman_urdu", "roman-urdu", "english", "en"):
            await ctx.reply("Use: urdu / roman / english", mention_author=False)
            return
        self.config.setdefault("ai", {})["language"] = lang
        try:
            save_config()
        except Exception:
            await ctx.reply("Saved in memory, but failed to write config.", mention_author=False)
            return
        await ctx.reply(f"AI language set to {lang}.", mention_author=False)

    @commands.command(name="ailangshow")
    @commands.guild_only()
    async def ailangshow(self, ctx: commands.Context):
        lang = self.config.get("ai", {}).get("language", "urdu")
        await ctx.reply(f"AI language: {lang}", mention_author=False)

    def cog_unload(self):
        asyncio.create_task(self.client.close())


async def setup(bot: commands.Bot):
    await bot.add_cog(AiCog(bot))
