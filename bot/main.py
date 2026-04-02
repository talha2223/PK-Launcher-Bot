import asyncio
import logging
import sys
import os
from pathlib import Path
from threading import Thread

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
if str(BASE_DIR / "bot") not in sys.path:
    sys.path.insert(0, str(BASE_DIR / "bot"))

import discord
from discord.ext import commands
from dotenv import load_dotenv

from utils.activity import ActivityManager
from utils.config import load_config
from utils.logging_setup import setup_logging
from utils.state import SharedState
from utils.api_server import run_api
from utils.storage import init_db

CONFIG_PATH = BASE_DIR / "config.json"

load_dotenv(dotenv_path=BASE_DIR / ".env")
load_dotenv(dotenv_path=BASE_DIR / "bot" / "cogs" / ".env", override=False)

config = load_config(CONFIG_PATH)
setup_logging(BASE_DIR / "logs")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=config["prefix"], intents=intents, help_command=None)

state = SharedState(default_users=config.get("default_users", 0))
activity = ActivityManager(bot, state, config)
bot.shared_state = state
bot.activity_manager = activity

@bot.event
async def on_ready():
    logging.info("Logged in as %s (%s)", bot.user, bot.user.id)
    if config.get("status_use_member_count", False):
        guild_id = int(config.get("guild_id", 0))
        guild = bot.get_guild(guild_id) if guild_id else (bot.guilds[0] if bot.guilds else None)
        if guild:
            state.users = guild.member_count or len(guild.members)
    await activity.update_status()

async def load_extensions():
    await bot.load_extension("cogs.commands")
    await bot.load_extension("cogs.utility")
    await bot.load_extension("cogs.moderation")
    await bot.load_extension("cogs.levels")
    await bot.load_extension("cogs.economy")
    await bot.load_extension("cogs.profile")
    await bot.load_extension("cogs.afk")
    await bot.load_extension("cogs.shop")
    await bot.load_extension("cogs.ai")
    await bot.load_extension("cogs.ai_moderation")
    await bot.load_extension("cogs.ai_autoreply")
    await bot.load_extension("cogs.music")
    await bot.load_extension("cogs.invites")
    await bot.load_extension("cogs.suggestions")
    await bot.load_extension("cogs.feedback")
    await bot.load_extension("cogs.giveaways")
    await bot.load_extension("cogs.logging_events")
    await bot.load_extension("events.welcome")
    await bot.load_extension("events.automod")
    await bot.load_extension("events.errors")
    await bot.load_extension("events.greeter")
    await bot.load_extension("events.status_members")
    await bot.load_extension("events.command_channel")
    await bot.load_extension("cogs.tickets")

async def main():
    await init_db()
    await load_extensions()

    api_host = config["api"]["host"]
    api_port = config["api"]["port"]
    api_token = config["api"]["auth_token"]

    api_thread = Thread(
        target=run_api,
        args=(state, activity, api_host, api_port, api_token, config.get("status_use_member_count", False)),
        daemon=True,
    )
    api_thread.start()

    token = os.getenv("DISCORD_BOT_TOKEN") or config.get("token", "")
    if token in ("PUT_DISCORD_BOT_TOKEN_HERE", "YOUR_DISCORD_BOT_TOKEN_HERE", ""):
        raise RuntimeError("Please set your Discord bot token in DISCORD_BOT_TOKEN environment variable or config.json")

    await bot.start(token)

if __name__ == "__main__":
    asyncio.run(main())
