import discord
import logging

class ActivityManager:
    def __init__(self, bot, state, config):
        self.bot = bot
        self.state = state
        self.config = config

    async def update_status(self, users_override: int | None = None):
        template = self.config.get("status_template", "Managing {users} PK Launcher Users")
        activity_type = self.config.get("status_activity_type", "watching").lower()
        users = self.state.users if users_override is None else users_override
        text = template.format(users=users)

        if activity_type == "playing":
            activity = discord.Game(name=text)
        else:
            activity = discord.Activity(type=discord.ActivityType.watching, name=text)

        await self.bot.change_presence(activity=activity)
        logging.info("Status updated: %s", text)
