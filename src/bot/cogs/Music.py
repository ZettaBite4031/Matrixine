import discord
from discord.ext import commands
import wavelink
from discord import Embed
import asyncio
import time
from typing import cast
import logging
import datetime as dt
import typing as t
import re

URL_REGEX = (
    r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s("
    r")<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
)


from ..view import PlayingView, SearchView, PlatformView


class Music(commands.Cog):
    """Controls the playback functionality of the bot"""

    def __init__(self, bot):
        self.bot = bot

    async def format_time(self, seconds):
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours > 0:
            return f"{int(hours)}:{int(minutes)}:{int(seconds)}"
        else:
            return f"{int(minutes)}:{str(int(seconds)).zfill(2)}"

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.wait_until_ready()
        nodes = [
            wavelink.Node(
                uri=self.bot.CONFIG.LavalinkURI, password=self.bot.CONFIG.LavalinkPasswd
            )
        ]
        await wavelink.Pool.connect(nodes=nodes, client=self.bot, cache_capacity=100)

    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload):
        self.bot.log(logging.INFO, f"Node {payload.session_id} is ready!")

    async def create_now_playing_embed(self, ctx, track: wavelink.Playable):
        player: wavelink.Player = ctx.guild.voice_client
        volume = player.volume
        embed = discord.Embed(
            title="Current Track", color=self.bot.COLOR, timestamp=dt.datetime.now()
        )
        embed.set_author(
            name="Track Info", icon_url=self.bot.user.avatar.url, url=track.uri
        )
        embed.set_footer(
            text=f"Requested by {ctx.author.display_name}",
            icon_url=ctx.author.avatar.url,
        )
        embed.set_image(url=track.artwork)
        embed.add_field(name="Track Title", value=f"```{track.title}```", inline=False)
        embed.add_field(name="Uploaded By", value=f"```{track.author}```", inline=True)
        embed.add_field(name="Volume", value=f"```{volume}/100```", inline=True)

        num_symbols = 34
        filled_character = "~"
        cursor_character = "~>"
        future_character = "-"

        track_duration_in_seconds = track.length / 1000
        current_position_in_seconds = player.position / 1000

        num_filled = int((player.position / track.length) * num_symbols)
        visual_string = (
            filled_character * num_filled
            + cursor_character
            + future_character * (num_symbols - num_filled)
        )
        track_duration = await self.format_time(track_duration_in_seconds)
        current_position = await self.format_time(current_position_in_seconds)
        embed.add_field(
            name="Position",
            value=f"```{track_duration}/{current_position}```\n```{visual_string}```",
            inline=False,
        )

        return embed

    @commands.guild_only()
    @commands.hybrid_command(
        name="join", description="Tell the bot to join a voice channel you are in."
    )
    async def _connect(
        self, ctx: commands.Context, *, channel: discord.VoiceChannel | None = None
    ):
        node = wavelink.NodePool.get_node()
        player = node.get_player(ctx.guild.id)
        try:
            channel = channel or ctx.author.channel.voice
        except AttributeError:
            return await ctx.send(
                "No voice channel to connect to. Please either provide one or join one."
            )
        player: wavelink.Player = await channel.connect(cls=wavelink.Player)
        return player

    @commands.guild_only()
    @commands.hybrid_command(
        name="play",
        description='Add music to queue with `/play <query>`\nTo avoid specifying a platform every time, add "yt:", "youtube:", or "ytsearch:" before each query',
    )
    async def _play(self, ctx: commands.Context, *, query: t.Optional[str]):
        if not query:
            self._resume(ctx)
            return

        player: wavelink.Player
        player = cast(wavelink.Player, ctx.voice_client)

        if not player:
            try:
                player = await ctx.author.voice.channel.connect(cls=wavelink.Player)
            except AttributeError:
                await ctx.send(
                    "Please join a voice channel first before using this command!"
                )
                return
            except discord.ClientException:
                await ctx.send("I was unable to join that voice channel!")
                return

        player.autoplay = wavelink.AutoPlayMode.enabled

        if not hasattr(player, "home"):
            player.home = ctx.channel
        elif player.home != ctx.channel:
            await ctx.send(f"You can only play songs in {player.home.mention}!")
            return

        query = query.strip("<>")
        if not re.match(URL_REGEX, query):
            if query.startswith(("youtube:", "yt:", "ytsearch:")):
                query = query.split(":")[1]
                query = f"ytsearch:{query}"
            elif query.startswith(("spotify:", "sp:", "spsearch:")):
                query = query.split(":")[1]
                query = f"spsearch:{query}"
            else:
                embed = discord.Embed(
                    title="Choose a platform",
                    description="You didn't input a link. Please select a platform to search on",
                    color=self.bot.COLOR,
                    timestamp=dt.datetime.now(),
                )
                embed.set_author(
                    name=ctx.author.display_name, icon_url=ctx.author.avatar.url
                )
                embed.set_footer(text=f"{len(player.queue)} tracks in queue.")
                platform_view = PlatformView(ctx)
                await ctx.send(embed=embed, view=platform_view)
                try:
                    await platform_view.wait()
                except asyncio.TimeoutError:
                    return await ctx.send("Menu timed out. Please try again")
                platform_view.stop()
                platform = platform_view.children[0].values[0]
                if platform == "youtube":
                    query = f"ytsearch:{query}"
                elif platform == "spotify":
                    query = f"spsearch:{query}"
                else:
                    return

        tracks = await wavelink.Pool.fetch_tracks(query)

        if not tracks:
            return await ctx.send(
                f"{ctx.author.mention} - Could not find any tracks with that query!"
            )

        if isinstance(tracks, wavelink.Playlist):
            added: int = await player.queue.put_wait(tracks)
            await ctx.send(
                f"Added the playlist **`{tracks.name}`** ({added} songs) to the queue"
            )
        elif len(tracks) == 1:
            track: wavelink.Playable = tracks[0]
            await player.queue.put_wait(tracks)
            await ctx.send(f"Added **`{track}`** to the queue")
        else:
            embed = self.get_choose_track_embed(ctx, tracks)
            search_view = SearchView(ctx, tracks[:5], player)
            await ctx.send(embed=embed, view=search_view)
            try:
                await search_view.wait()
            except asyncio.TimeoutError:
                return await ctx.send("Menu timed out. Please try again")
            search_view.stop()

        if not player.playing:
            await player.play(player.queue.get(), volume=30)

    def get_choose_track_embed(self, ctx, tracks):
        embed = discord.Embed(
            title="Choose a song",
            description=(
                "\n".join(
                    f"**{i + 1}.** {t.title} ({t.length // 60000}:{str(t.length % 60).zfill(2)})"
                    for i, t in enumerate(tracks[:5])
                )
            ),
            color=self.bot.COLOR,
            timestamp=dt.datetime.now(),
        )
        embed.set_author(name="Search results", icon_url=ctx.author.avatar.url)
        embed.set_footer(
            text=f"Queried by {ctx.author.display_name}",
            icon_url=self.bot.user.avatar.url,
        )
        return embed

    @commands.guild_only()
    @commands.hybrid_command(
        name="nowplaying",
        aliases=["np"],
        description="Show current player with current song playing.",
    )
    async def _nowplaying(self, ctx):
        player: wavelink.Player = ctx.guild.voice_client
        if player and player.playing:
            # Send the initial message
            curr_track = player.current
            embed = await self.create_now_playing_embed(ctx, curr_track)
            await ctx.send(embed=embed, view=PlayingView(ctx, player))
        else:
            await ctx.send("Nothing is currently playing.")

    @commands.guild_only()
    @commands.hybrid_command(
        name="queue", aliases=["q"], description="View the top ten songs in the queue."
    )
    async def _queue(self, ctx):
        player: wavelink.Player = ctx.guild.voice_client
        if not player or not player.connected:
            await ctx.send("I am not connected to a voice channel.")
            return
        if not player.queue:
            await ctx.send("The queue is empty.")
            return
        # Get the first 10 items in the queue and number them
        queue_items = []
        for i, item in enumerate(player.queue):
            if i >= 10:
                break
            queue_items.append(f"```{i + 1}. {str(item)}```")
        # Join the numbered items with "\n" separator
        queue_str = "\n".join(queue_items)
        embed = Embed(title="🎵 Queue (First 10 Songs)")
        embed.add_field(name="Queue:", value=queue_str, inline=False)
        embed.set_footer(text=f"{len(player.queue)} songs in queue.")
        await ctx.send(embed=embed)

    @commands.guild_only()
    @commands.hybrid_command(name="skip", aliases=["s"], description="Skip a song.")
    async def _skip(self, ctx):
        player: wavelink.Player = ctx.guild.voice_client
        if player and player.playing:
            await player.stop(force=True)
            await ctx.send("```Skipped the current song.```")
        else:
            await ctx.send("```⛔ Nothing is currently playing.```")

    @commands.guild_only()
    @commands.hybrid_command(
        name="previous", aliases=["prev"], description="View the previous song."
    )
    async def _previous(self, ctx):
        player: wavelink.Player = ctx.guild.voice_client
        if player and len(player.queue.history) > 0:
            prev_track = player.queue.history[-2]  # Get the last song in the history
            await player.play(prev_track)
            await ctx.send(f"```Playing **{prev_track.title}**```")
        else:
            await ctx.send("```⛔ No previous track to play.```")

    @commands.guild_only()
    @commands.hybrid_command(
        name="clear", aliases=["cls"], description="Clear all the songs from queue."
    )
    async def _clearqueue(self, ctx):
        player: wavelink.Player = ctx.guild.voice_client
        if player:
            player.queue.reset()
            await ctx.send("```Queue cleared.```")
        else:
            await ctx.send("```⛔ No queue to clear.```")

    @commands.guild_only()
    @commands.hybrid_command(
        name="shuffle", description="Shuffle all the songs in the queue."
    )
    async def _shuffle(self, ctx):
        player: wavelink.Player = ctx.guild.voice_client
        if player:
            player.queue.shuffle()
            await ctx.send("```Queue Shuffled.```")
        else:
            return await ctx.send("```⛔ The bot is disconnected.```")

    @commands.guild_only()
    @commands.hybrid_command(
        name="pause", description="Pause the current playing song."
    )
    async def _pause(self, ctx):
        player: wavelink.Player = ctx.guild.voice_client
        if player:
            await player.pause(True)
            await ctx.send("Paused")
        else:
            return await ctx.send("```⛔ The bot is disconnected.```")

    @commands.guild_only()
    @commands.hybrid_command(
        name="resume", description="Resume the current playing song."
    )
    async def _resume(self, ctx):
        player: wavelink.Player = ctx.guild.voice_client
        if player:
            await player.pause(False)
            await ctx.send("Resumed.")
        else:
            return await ctx.send("```⛔ The bot is disconnected.```")

    @commands.guild_only()
    @commands.hybrid_command(
        name="stop", description="Disconnect bot from the voice channel."
    )
    async def _disconnect(self, ctx):
        player: wavelink.Player = ctx.guild.voice_client
        if player:
            await player.disconnect()
            await ctx.send("```⛔ Disconnected```")
        else:
            return await ctx.send("```⛔ The bot is not connected.```")

    @commands.guild_only()
    @commands.hybrid_command(
        name="volume", description="Set the volume for the bot from 0% to 100%."
    )
    async def _vol(self, ctx, volume: int):
        player: wavelink.Player = ctx.guild.voice_client
        if volume > 100:
            return await ctx.send("```⛔ 100% Is Max```")
        elif volume < 0:
            return await ctx.send("```⛔ 0% Is Lowest```")
        await player.set_volume(volume)
        await ctx.send(f"```Volume set to %{volume}```")

    @commands.guild_only()
    @commands.hybrid_command(name="repeatall", description="Repeat the queue.")
    async def _loopall(self, ctx):
        player: wavelink.Player = ctx.guild.voice_client
        if player:
            if player.queue.mode == wavelink.QueueMode.loop_all:
                player.queue.mode = wavelink.QueueMode.normal
                await ctx.send("Repeat off.")
            else:
                player.queue.mode = wavelink.QueueMode.loop_all
                await ctx.send("```Repeat on.```")
        else:
            await ctx.send(f"```⛔ No player connected.```")

    @commands.guild_only()
    @commands.hybrid_command(name="repeat", description="Repeat the current song.")
    async def _loop(self, ctx):
        player: wavelink.Player = ctx.guild.voice_client
        if player:
            if player.queue.mode == wavelink.QueueMode.loop:
                player.queue.mode = wavelink.QueueMode.normal
                await ctx.send("Repeat off.")
            else:
                player.queue.mode = wavelink.QueueMode.loop
                await ctx.send("```Repeat on.```")
        else:
            await ctx.send(f"```⛔ No player connected.```")


async def setup(bot):
    cog = Music(bot)
    await bot.add_cog(cog)
