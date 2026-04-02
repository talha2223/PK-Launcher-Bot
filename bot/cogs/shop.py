import discord
from discord.ext import commands

from utils.config import get_config, save_config
from utils.permissions import admin_only
from utils.storage import get_balance, get_economy, set_economy


DEFAULT_ITEMS = [
    {
        "id": "vip",
        "name": "VIP Role",
        "price": 500,
        "type": "role",
        "role_id": 0,
        "role_name": "VIP",
        "description": "Exclusive VIP access",
    }
]


class ShopCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config = get_config()

    def _items(self):
        shop_cfg = self.config.get("shop", {})
        items = shop_cfg.get("items")
        if not items:
            return DEFAULT_ITEMS
        return items

    def _find_item(self, item_id: str):
        item_id = item_id.lower()
        for item in self._items():
            if str(item.get("id", "")).lower() == item_id:
                return item
        return None

    @commands.command(name="shop")
    @commands.guild_only()
    async def shop(self, ctx: commands.Context):
        items = self._items()
        if not items:
            await ctx.reply("Shop not configured.", mention_author=False)
            return

        embed = discord.Embed(title="PK Launcher Shop", color=discord.Color.blurple())
        lines = []
        for item in items:
            item_id = item.get("id", "?")
            name = item.get("name", "Item")
            price = item.get("price", 0)
            desc = item.get("description", "")
            lines.append(f"`{item_id}` — {name} ({price} coins) {desc}")
        embed.description = "\n".join(lines)
        await ctx.reply(embed=embed, mention_author=False)

    @commands.command(name="buy")
    @commands.guild_only()
    async def buy(self, ctx: commands.Context, item_id: str):
        item = self._find_item(item_id)
        if not item:
            await ctx.reply("Item not found. Use `!shop`.", mention_author=False)
            return

        price = int(item.get("price", 0))
        data = await get_economy(ctx.guild.id, ctx.author.id)
        coins = data["coins"]
        if coins < price:
            await ctx.reply(f"Not enough coins. You need {price} coins.", mention_author=False)
            return

        if item.get("type") == "role":
            role = None
            role_id = int(item.get("role_id", 0)) if item.get("role_id") else 0
            role_name = (item.get("role_name") or "").strip()
            if role_id:
                role = ctx.guild.get_role(role_id)
            if role is None and role_name:
                role = discord.utils.get(ctx.guild.roles, name=role_name)
            if not role:
                await ctx.reply("Role not configured for this item.", mention_author=False)
                return
            if role in ctx.author.roles:
                await ctx.reply("You already own this role.", mention_author=False)
                return

            try:
                await ctx.author.add_roles(role, reason="Shop purchase")
            except discord.Forbidden:
                await ctx.reply("I don't have permission to assign that role.", mention_author=False)
                return

        coins -= price
        await set_economy(ctx.guild.id, ctx.author.id, coins, data["streak"], data["last_claim"])
        await ctx.reply(f"Purchase successful! Remaining coins: {coins}", mention_author=False)

    @commands.command(name="inventory", aliases=["inv", "bag"])
    @commands.guild_only()
    async def inventory(self, ctx: commands.Context):
        coins = await get_balance(ctx.guild.id, ctx.author.id)
        owned = []
        for item in self._items():
            if item.get("type") == "role":
                role_id = int(item.get("role_id", 0)) if item.get("role_id") else 0
                role_name = (item.get("role_name") or "").strip()
                role = ctx.guild.get_role(role_id) if role_id else discord.utils.get(ctx.guild.roles, name=role_name)
                if role and role in ctx.author.roles:
                    owned.append(item.get("name", "Role"))

        embed = discord.Embed(title=f"{ctx.author.display_name}'s Inventory", color=discord.Color.green())
        embed.add_field(name="Coins", value=str(coins), inline=False)
        embed.add_field(name="Owned", value="\n".join(owned) if owned else "None", inline=False)
        await ctx.reply(embed=embed, mention_author=False)

    @commands.command(name="setshoprole")
    @commands.guild_only()
    @admin_only()
    async def setshoprole(self, ctx: commands.Context, item_id: str, role: discord.Role):
        item = self._find_item(item_id)
        if not item:
            await ctx.reply("Item not found. Use `!shop` to see IDs.", mention_author=False)
            return
        item["role_id"] = role.id
        item["role_name"] = role.name

        self.config.setdefault("shop", {})["items"] = self._items()
        try:
            save_config()
        except Exception:
            await ctx.reply("Saved in memory, but failed to write config.", mention_author=False)
            return

        await ctx.reply(f"Updated {item_id} to role {role.mention}.", mention_author=False)


async def setup(bot: commands.Bot):
    await bot.add_cog(ShopCog(bot))
