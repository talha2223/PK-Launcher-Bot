from discord.ext import commands

from utils.config import get_config


def is_admin(member) -> bool:
    if not member:
        return False

    if getattr(member.guild_permissions, "administrator", False):
        return True

    config = get_config()
    role_names = [r.lower() for r in config.get("admin_role_names", ["🔧 Admin"])]
    member_roles = [r.name.lower() for r in getattr(member, "roles", [])]
    return any(rn in member_roles for rn in role_names)


def admin_only():
    async def predicate(ctx: commands.Context):
        return is_admin(ctx.author)

    return commands.check(predicate)
