import asyncio
import logging
import re
import shutil
from pathlib import Path

import discord
from discord.ext import commands
import yt_dlp

from utils.config import get_config

URL_RE = re.compile(r"https?://", re.IGNORECASE)

YTDL_OPTIONS = {
    "format": "bestaudio/best",
    "quiet": True,
    "no_warnings": True,
    "noplaylist": True,
    "source_address": "0.0.0.0",
    "geo_bypass": True,
    "default_search": "ytsearch5",
}

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get("title")
        self.url = data.get("url")
        self.webpage_url = data.get("webpage_url")
        self.duration = data.get("duration")

    @classmethod
    async def create(cls, query: str, *, loop, stream=True, volume=0.5, ffmpeg_executable=None):
        opts = dict(YTDL_OPTIONS)
        ytdl = yt_dlp.YoutubeDL(opts)

        if URL_RE.match(query):
            target = query
        else:
            target = f"ytsearch5:{query}"

        data = await loop.run_in_executor(
            None, lambda: ytdl.extract_info(target, download=not stream)
        )

        if "entries" in data:
            data = data["entries"][0] if data["entries"] else None

        if not data:
            raise RuntimeError("No audio results found")

        filename = data["url"] if stream else ytdl.prepare_filename(data)
        audio = discord.FFmpegPCMAudio(filename, executable=ffmpeg_executable, **FFMPEG_OPTIONS)
        return cls(audio, data=data, volume=volume)


class MusicState:
    def __init__(self):
        self.queue = []
        self.current = None
        self.lock = asyncio.Lock()


class MusicControlsView(discord.ui.View):
    def __init__(self, cog, guild_id: int):
        super().__init__(timeout=300)
        self.cog = cog
        self.guild_id = guild_id

    def _voice_check(self, interaction: discord.Interaction):
        guild = interaction.guild
        if not guild:
            return False, "This can only be used in a server."
        voice = guild.voice_client
        if not voice:
            return False, "I am not connected to a voice channel."
        if not interaction.user.voice:
            return False, "You must be in a voice channel."
        if interaction.user.voice.channel != voice.channel:
            return False, "You must be in the same voice channel as me."
        return True, None

    @discord.ui.button(label="Pause", style=discord.ButtonStyle.secondary)
    async def pause_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        ok, msg = self._voice_check(interaction)
        if not ok:
            await interaction.response.send_message(msg, ephemeral=True)
            return
        voice = interaction.guild.voice_client
        if voice and voice.is_playing():
            voice.pause()
            await interaction.response.send_message("Paused.", ephemeral=True)
        else:
            await interaction.response.send_message("Nothing is playing.", ephemeral=True)

    @discord.ui.button(label="Resume", style=discord.ButtonStyle.success)
    async def resume_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        ok, msg = self._voice_check(interaction)
        if not ok:
            await interaction.response.send_message(msg, ephemeral=True)
            return
        voice = interaction.guild.voice_client
        if voice and voice.is_paused():
            voice.resume()
            await interaction.response.send_message("Resumed.", ephemeral=True)
        else:
            await interaction.response.send_message("Nothing is paused.", ephemeral=True)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary)
    async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        ok, msg = self._voice_check(interaction)
        if not ok:
            await interaction.response.send_message(msg, ephemeral=True)
            return
        voice = interaction.guild.voice_client
        if voice and voice.is_playing():
            voice.stop()
            await interaction.response.send_message("Skipped.", ephemeral=True)
        else:
            await interaction.response.send_message("Nothing is playing.", ephemeral=True)

    @discord.ui.button(label="Stop", style=discord.ButtonStyle.danger)
    async def stop_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        ok, msg = self._voice_check(interaction)
        if not ok:
            await interaction.response.send_message(msg, ephemeral=True)
            return
        state = self.cog.get_state(self.guild_id)
        state.queue.clear()
        state.current = None
        voice = interaction.guild.voice_client
        if voice:
            voice.stop()
            self.cog.schedule_idle_disconnect(self.guild_id, voice)
        await interaction.response.send_message("Stopped and cleared queue.", ephemeral=True)

    @discord.ui.button(label="Queue", style=discord.ButtonStyle.secondary)
    async def queue_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        ok, msg = self._voice_check(interaction)
        if not ok:
            await interaction.response.send_message(msg, ephemeral=True)
            return
        state = self.cog.get_state(self.guild_id)
        if not state.queue:
            await interaction.response.send_message("Queue is empty.", ephemeral=True)
            return
        lines = [f"{idx}. {item.title}" for idx, item in enumerate(state.queue[:10], start=1)]
        await interaction.response.send_message("Upcoming:\n" + "\n".join(lines), ephemeral=True)


class MusicCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config = get_config()
        self.states: dict[int, MusicState] = {}
        self.idle_tasks: dict[int, asyncio.Task] = {}
        self.alone_tasks: dict[int, asyncio.Task] = {}
        self.ffmpeg_executable = self._resolve_ffmpeg()
        if not self.ffmpeg_executable:
            logging.warning("FFmpeg not found. Music playback will fail.")

    def _resolve_ffmpeg(self):
        cfg = self.config.get("ffmpeg_path")
        if cfg:
            p = Path(cfg)
            if not p.is_absolute():
                p = (Path(__file__).resolve().parent.parent.parent / p).resolve()
            if p.exists():
                return str(p)
        exe = shutil.which("ffmpeg")
        return exe

    def get_state(self, guild_id: int) -> MusicState:
        if guild_id not in self.states:
            self.states[guild_id] = MusicState()
        return self.states[guild_id]

    def cancel_idle(self, guild_id: int):
        task = self.idle_tasks.pop(guild_id, None)
        if task and not task.done():
            task.cancel()

    def schedule_idle_disconnect(self, guild_id: int, voice: discord.VoiceClient):
        self.cancel_idle(guild_id)
        seconds = int(self.config.get("music_idle_disconnect_seconds", 180))

        async def _idle():
            try:
                await asyncio.sleep(seconds)
                state = self.get_state(guild_id)
                if voice.is_playing() or voice.is_paused() or state.queue:
                    return
                await voice.disconnect()
            except Exception:
                pass

        self.idle_tasks[guild_id] = self.bot.loop.create_task(_idle())

    def _cancel_alone(self, guild_id: int):
        task = self.alone_tasks.pop(guild_id, None)
        if task and not task.done():
            task.cancel()

    def _schedule_alone_disconnect(self, guild: discord.Guild, voice: discord.VoiceClient):
        self._cancel_alone(guild.id)
        seconds = int(self.config.get("voice_alone_disconnect_seconds", 60))

        async def _alone():
            try:
                await asyncio.sleep(seconds)
                if not voice.is_connected():
                    return
                if voice.channel and len(voice.channel.members) <= 1:
                    await voice.disconnect()
            except Exception:
                pass

        self.alone_tasks[guild.id] = self.bot.loop.create_task(_alone())

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if not member.guild:
            return
        voice = member.guild.voice_client
        if not voice or not voice.channel:
            return

        # if bot is alone in channel, schedule disconnect
        if len(voice.channel.members) <= 1:
            self._schedule_alone_disconnect(member.guild, voice)
        else:
            self._cancel_alone(member.guild.id)

    def _controls_view(self, guild_id: int):
        return MusicControlsView(self, guild_id)

    async def ensure_voice(self, ctx: commands.Context):
        if ctx.author.voice is None:
            await ctx.reply("You must be in a voice channel.", mention_author=False)
            return None

        channel = ctx.author.voice.channel
        me = ctx.guild.me
        if me:
            perms = channel.permissions_for(me)
            if not perms.connect:
                await ctx.reply("I don't have permission to connect to that voice channel.", mention_author=False)
                return None
            if not perms.speak:
                await ctx.reply("I don't have permission to speak in that voice channel.", mention_author=False)
                return None

        if ctx.voice_client is None:
            return await channel.connect()
        if ctx.voice_client.channel != channel:
            await ctx.voice_client.move_to(channel)
        return ctx.voice_client

    def _play_next(self, guild_id: int, voice: discord.VoiceClient):
        state = self.get_state(guild_id)
        if not state.queue:
            state.current = None
            self.schedule_idle_disconnect(guild_id, voice)
            return
        source = state.queue.pop(0)
        state.current = source
        try:
            voice.play(
                source,
                after=lambda e: self.bot.loop.call_soon_threadsafe(self._play_next, guild_id, voice),
            )
        except Exception:
            self.schedule_idle_disconnect(guild_id, voice)

    @commands.command(name="join")
    async def join(self, ctx: commands.Context):
        voice = await self.ensure_voice(ctx)
        if voice:
            await ctx.reply("Joined voice channel.", mention_author=False)

    @commands.command(name="leave")
    async def leave(self, ctx: commands.Context):
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            await ctx.reply("Disconnected.", mention_author=False)
        state = self.get_state(ctx.guild.id)
        state.queue.clear()
        state.current = None
        self.cancel_idle(ctx.guild.id)

    @commands.command(name="play")
    async def play(self, ctx: commands.Context, *, query: str):
        voice = await self.ensure_voice(ctx)
        if voice is None:
            return

        state = self.get_state(ctx.guild.id)
        async with state.lock:
            volume = float(self.config.get("music", {}).get("default_volume", 0.5))
            try:
                source = await YTDLSource.create(
                    query,
                    loop=self.bot.loop,
                    stream=True,
                    volume=volume,
                    ffmpeg_executable=self.ffmpeg_executable,
                )
            except Exception:
                logging.exception("yt-dlp error")
                await ctx.reply("Failed to load that audio. Try another link or query.", mention_author=False)
                return

            self.cancel_idle(ctx.guild.id)
            if voice.is_playing() or voice.is_paused():
                if len(state.queue) >= self.config.get("music", {}).get("max_queue", 50):
                    await ctx.reply("Queue is full.", mention_author=False)
                    return
                state.queue.append(source)
                await ctx.reply(f"Queued: **{source.title}**", mention_author=False)
            else:
                state.current = source
                try:
                    voice.play(
                        source,
                        after=lambda e: self.bot.loop.call_soon_threadsafe(self._play_next, ctx.guild.id, voice),
                    )
                except Exception:
                    await ctx.reply("Failed to start playback. Is FFmpeg installed?", mention_author=False)
                    return
                await ctx.reply(
                    f"Now playing: **{source.title}**",
                    mention_author=False,
                    view=self._controls_view(ctx.guild.id),
                )

    @commands.command(name="controls")
    async def controls(self, ctx: commands.Context):
        await ctx.reply("Music controls:", view=self._controls_view(ctx.guild.id), mention_author=False)

    @commands.command(name="skip")
    async def skip(self, ctx: commands.Context):
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.stop()
            await ctx.reply("Skipped.", mention_author=False)

    @commands.command(name="pause")
    async def pause(self, ctx: commands.Context):
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            await ctx.reply("Paused.", mention_author=False)

    @commands.command(name="resume")
    async def resume(self, ctx: commands.Context):
        if ctx.voice_client and ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.reply("Resumed.", mention_author=False)

    @commands.command(name="stop")
    async def stop(self, ctx: commands.Context):
        state = self.get_state(ctx.guild.id)
        state.queue.clear()
        state.current = None
        if ctx.voice_client:
            ctx.voice_client.stop()
        self.schedule_idle_disconnect(ctx.guild.id, ctx.voice_client) if ctx.voice_client else None
        await ctx.reply("Stopped and cleared queue.", mention_author=False)

    @commands.command(name="queue")
    async def queue(self, ctx: commands.Context):
        state = self.get_state(ctx.guild.id)
        if not state.queue:
            await ctx.reply("Queue is empty.", mention_author=False)
            return
        lines = [f"{idx}. {item.title}" for idx, item in enumerate(state.queue[:10], start=1)]
        await ctx.reply("Upcoming:\n" + "\n".join(lines), mention_author=False)

    @commands.command(name="now")
    async def now(self, ctx: commands.Context):
        state = self.get_state(ctx.guild.id)
        if not state.current:
            await ctx.reply("Nothing is playing.", mention_author=False)
            return
        await ctx.reply(
            f"Now playing: **{state.current.title}**",
            mention_author=False,
            view=self._controls_view(ctx.guild.id),
        )

    @commands.command(name="volume")
    async def volume(self, ctx: commands.Context, volume: int):
        if not ctx.voice_client or not ctx.voice_client.source:
            await ctx.reply("Nothing is playing.", mention_author=False)
            return
        if volume < 0 or volume > 100:
            await ctx.reply("Volume must be between 0 and 100.", mention_author=False)
            return
        ctx.voice_client.source.volume = volume / 100
        await ctx.reply(f"Volume set to {volume}%.", mention_author=False)


async def setup(bot: commands.Bot):
    await bot.add_cog(MusicCog(bot))
