from discord.ext import commands

EXAMPLES = {
    "download": "!download",
    "version": "!version",
    "install": "!install",
    "setwelcome": "!setwelcome #welcome",
    "setrules": "!setrules #rules",
    "setwelcomemsg": "!setwelcomemsg Welcome {user} to {server}! Read {rules}.",
    "setsuggest": "!setsuggest #suggestions",
    "setcommands": "!setcommands #commands",
    "setreports": "!setreports #reports",
    "setreviews": "!setreviews #reviews",
    "ticketsetup": "!ticketsetup Support,Bug,Purchase",
    "ticketpanel": "!ticketpanel",
    "ticketclose": "!ticketclose",
    "gstart": "!gstart 10m 1 Nitro",
    "gend": "!gend 123456789012345678",
    "greroll": "!greroll 123456789012345678",
    "invites": "!invites",
    "invite": "!invite @user",
    "invited": "!invited @user",
    "kick": "!kick @user Spamming",
    "ban": "!ban @user Repeated abuse",
    "unban": "!unban 123456789012345678",
    "timeout": "!timeout @user 10 Spamming",
    "untimeout": "!untimeout @user",
    "purge": "!purge 20",
    "play": "!play https://youtube.com/...",
    "controls": "!controls",
    "volume": "!volume 50",
    "rank": "!rank",
    "leaderboard": "!leaderboard",
    "suggest": "!suggest Add a new feature",
    "report": "!report Launcher keeps crashing on login",
    "review": "!review 5 Amazing launcher!",
    "reviewtop": "!reviewtop 7",
    "members": "!members",
    "warn": "!warn @user Spamming",
    "tatti": "!tatti 5 @user",
    "addbad": "!addbad badword",
    "removebad": "!removebad badword",
    "setvip": "!setvip @VIP",
    "afk": "!afk Lunch break",
    "profile": "!profile",
    "daily": "!daily",
    "balance": "!balance",
    "countdown": "!countdown 2026-03-01 Launch Day",
    "shop": "!shop",
    "buy": "!buy vip",
    "inventory": "!inventory",
    "setshoprole": "!setshoprole vip @VIP",
    "ai": "!ai How to install PK Launcher?",
    "ask": "!ask How to download?",
    "summarize": "!summarize Paste text here",
    "rewrite": "!rewrite Make this message polite",
    "teach": "!teach How to install? | Download and run installer.",
    "forget": "!forget How to install?",
    "ailang": "!ailang urdu",
    "ailangshow": "!ailangshow",
    "aimod": "!aimod on",
    "setaimod": "!setaimod #mod-logs",
    "aiauto": "!aiauto on",
    "setaiautoignore": "!setaiautoignore #general",
}


class ErrorHandler(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if hasattr(ctx.command, "on_error"):
            return

        if isinstance(error, commands.CommandNotFound):
            return

        if isinstance(error, (commands.MissingRequiredArgument, commands.BadArgument, commands.UserInputError)):
            usage = f"Usage: {ctx.prefix}{ctx.command.qualified_name} {ctx.command.signature}".strip()
            example = EXAMPLES.get(ctx.command.name)
            msg = usage
            if example:
                msg = f"{usage}\nExample: {example}"
            await ctx.reply(msg, mention_author=False)
            return

        if isinstance(error, commands.CheckFailure):
            await ctx.reply("You don't have permission to use this command.", mention_author=False)
            return

        if isinstance(error, commands.CommandOnCooldown):
            await ctx.reply(f"Cooldown. Try again in {error.retry_after:.1f}s.", mention_author=False)
            return

        raise error


async def setup(bot: commands.Bot):
    await bot.add_cog(ErrorHandler(bot))
