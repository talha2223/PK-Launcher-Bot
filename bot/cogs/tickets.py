import asyncio
import discord
from discord.ext import commands
from discord.ui import View, Select, Button
from datetime import datetime
from pathlib import Path

from utils.config import get_config
from utils.permissions import admin_only
from utils.storage import (
    get_ticket_categories,
    get_ticket_panel_channel_id,
    get_ticket_panel_message_id,
    set_ticket_categories,
    set_ticket_panel_channel_id,
    set_ticket_panel_message_id,
)

TRANSCRIPT_DIR = Path(__file__).resolve().parent.parent.parent / "transcripts"


class TicketCategorySelect(Select):
    def __init__(self, bot: commands.Bot, guild_id: int, categories: list[tuple[str, int]]):
        options = [discord.SelectOption(label=label, value=label) for label, _ in categories]
        super().__init__(
            placeholder="Select a ticket category",
            min_values=1,
            max_values=1,
            options=options,
            custom_id=f"ticket_select_{guild_id}",
        )
        self.bot = bot
        self.guild_id = guild_id
        self.categories = {label: category_id for label, category_id in categories}

    async def callback(self, interaction: discord.Interaction):
        label = self.values[0]
        category_id = self.categories.get(label)
        if not category_id:
            await interaction.response.send_message("Category not found. Please run !ticketsetup again.", ephemeral=True)
            return

        guild = interaction.guild
        user = interaction.user
        category = guild.get_channel(category_id)
        if category is None:
            await interaction.response.send_message("Category missing. Please run !ticketsetup again.", ephemeral=True)
            return

        me = guild.me
        if me and not me.guild_permissions.manage_channels:
            await interaction.response.send_message("I need Manage Channels permission to create tickets.", ephemeral=True)
            return

        existing = discord.utils.get(guild.text_channels, name=f"ticket-{user.id}")
        if existing:
            await interaction.response.send_message("You already have an open ticket.", ephemeral=True)
            return

        config = get_config()
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        }

        support_role_id = config.get("ticket_support_role_id", 0)
        if support_role_id:
            role = guild.get_role(support_role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

        try:
            channel = await guild.create_text_channel(
                name=f"ticket-{user.id}",
                category=category,
                overwrites=overwrites,
                topic=f"Ticket for {user.id} ({label})",
            )
        except Exception:
            await interaction.response.send_message("Failed to create ticket channel. Check my permissions.", ephemeral=True)
            return

        await channel.send(
            f"Hello {user.display_name}, a support member will assist you shortly.",
            view=TicketCloseView(self.bot),
        )
        await interaction.response.send_message(f"Ticket created: {channel.mention}", ephemeral=True)


class TicketPanelView(View):
    def __init__(self, bot: commands.Bot, guild_id: int, categories: list[tuple[str, int]]):
        super().__init__(timeout=None)
        self.add_item(TicketCategorySelect(bot, guild_id, categories))


class TicketCloseView(View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.red, custom_id="ticket_close")
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message("This is not a ticket channel.", ephemeral=True)
            return

        await interaction.response.send_message("Closing ticket and saving transcript...", ephemeral=True)

        messages = []
        async for msg in channel.history(limit=None, oldest_first=True):
            timestamp = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
            content = msg.content.replace("\n", " ")
            messages.append(f"[{timestamp}] {msg.author}: {content}")

        TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)
        transcript_path = TRANSCRIPT_DIR / f"{channel.name}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.txt"
        transcript_path.write_text("\n".join(messages), encoding="utf-8")

        await channel.delete(reason="Ticket closed")


class TicketsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        self.bot.add_view(TicketCloseView(self.bot))
        asyncio.create_task(self._register_views())

    async def _register_views(self):
        if not self.bot.is_ready():
            await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            categories = await get_ticket_categories(guild.id)
            if categories:
                self.bot.add_view(TicketPanelView(self.bot, guild.id, categories))
                await self._ensure_panel_message(guild, categories)

    async def _ensure_panel_message(self, guild: discord.Guild, categories: list[tuple[str, int]]):
        channel_id = await get_ticket_panel_channel_id(guild.id)
        message_id = await get_ticket_panel_message_id(guild.id)
        if not channel_id:
            return
        channel = guild.get_channel(channel_id)
        if not channel:
            return
        view = TicketPanelView(self.bot, guild.id, categories)
        self.bot.add_view(view)

        if message_id:
            try:
                msg = await channel.fetch_message(message_id)
                await msg.edit(view=view)
                return
            except Exception:
                pass

        embed = discord.Embed(title="Support Tickets", description="Select a category to open a ticket.")
        try:
            msg = await channel.send(embed=embed, view=view)
        except discord.Forbidden:
            msg = await channel.send("Select a category to open a ticket:", view=view)
        await set_ticket_panel_message_id(guild.id, msg.id)

    async def _send_panel(self, ctx: commands.Context, categories: list[tuple[str, int]]):
        embed = discord.Embed(title="Support Tickets", description="Select a category to open a ticket.")
        view = TicketPanelView(self.bot, ctx.guild.id, categories)
        self.bot.add_view(view)
        try:
            msg = await ctx.send(embed=embed, view=view)
        except discord.Forbidden:
            msg = await ctx.send("Select a category to open a ticket:", view=view)
        await set_ticket_panel_message_id(ctx.guild.id, msg.id)

    @commands.command(name="ticketsetup")
    @commands.guild_only()
    @admin_only()
    async def ticket_setup(self, ctx: commands.Context, *, categories: str):
        me = ctx.guild.me
        if me and not me.guild_permissions.manage_channels:
            await ctx.reply("I need Manage Channels permission to set up tickets.", mention_author=False)
            return

        labels = [c.strip() for c in categories.split(",") if c.strip()]
        if not labels:
            await ctx.reply("Provide categories like: !ticketsetup Support,Bug,Purchase", mention_author=False)
            return

        created = []
        for label in labels:
            existing = discord.utils.get(ctx.guild.categories, name=label)
            if existing:
                created.append((label, existing.id))
                continue
            try:
                category = await ctx.guild.create_category(name=label)
                created.append((label, category.id))
            except Exception:
                await ctx.reply(f"Failed to create category: {label}", mention_author=False)
                return

        await set_ticket_categories(ctx.guild.id, created)
        await set_ticket_panel_channel_id(ctx.guild.id, ctx.channel.id)

        await self._send_panel(ctx, created)
        await ctx.reply("Ticket panel created.", mention_author=False)

    @commands.command(name="ticketpanel")
    @commands.guild_only()
    @admin_only()
    async def ticket_panel(self, ctx: commands.Context):
        categories = await get_ticket_categories(ctx.guild.id)
        if not categories:
            await ctx.reply("No ticket categories found. Run !ticketsetup first.", mention_author=False)
            return
        await set_ticket_panel_channel_id(ctx.guild.id, ctx.channel.id)
        await self._send_panel(ctx, categories)

    @commands.command(name="ticketclose")
    @commands.guild_only()
    @admin_only()
    async def ticket_close(self, ctx: commands.Context):
        await ctx.send("Press the button below to close this ticket.", view=TicketCloseView(self.bot))


async def setup(bot: commands.Bot):
    await bot.add_cog(TicketsCog(bot))
