#!/usr/bin/env python3
import os
from typing import Generator
import discord
import logging
import wavelink
import asyncio
from discord.ext import commands

LAVALINK_PASS = os.environ["LAVALINK_PASS"]
PREFIXES = ":", ";", "!", ">", "/", "."


class Bot(commands.Bot):
    def __init__(self) -> None:
        intents: discord.Intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix=PREFIXES, intents=intents)
        self.setup_logging()
        self.remove_command("help")
        self.prefixes = PREFIXES
        # self.members: Generator[discord.Member, None, None] = self.get_all_members()
        self.owner: discord.User | None = self.get_user(
            self.owner_id if self.owner_id else int(os.environ["OWNER_ID"])
        )
        self.connected_channel: discord.VoiceChannel | None = None

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        """Disconnect the bot when it's is alone in a voice channel"""
        voice: discord.VoiceProtocol | None
        if not member.id == self.user.id:  # type:ignore
            return
        elif (
            not before.channel
            and after.channel
            and (voice := after.channel.guild.voice_client)
        ):
            while True:
                await asyncio.sleep(120)
                if after.channel and len(after.channel.members) == 1:
                    embed: discord.Embed = discord.Embed(
                        title="Bot Disconnected",
                        description=f"Disconnecting from `{after.channel.name}`.\nReason: I'm alone 😢",
                    )
                    await self.home_channel.send(embed=embed)
                    await voice.disconnect(force=False)
                    break

    def setup_logging(self) -> None:
        # Set up logging
        logging.basicConfig(
            filename="./bot.log",
            level=logging.INFO,
            format="%(asctime)s:%(levelname)s:%(message)s",
        )
        handler: logging.StreamHandler = logging.StreamHandler()
        formatter: discord.utils._ColourFormatter = discord.utils._ColourFormatter()
        # Custom date formatting
        formatter.FORMATS = {
            level: logging.Formatter(
                f"\x1b[30;1m%(asctime)s\x1b[0m {colour}%(levelname)-8s\x1b[0m \x1b[35m%(name)s\x1b[0m %(message)s",
                "%m-%d-%Y %H:%M:%S",
            )
            for level, colour in formatter.LEVEL_COLOURS
        }
        discord.utils.setup_logging(
            level=logging.INFO,
            formatter=formatter,
            handler=handler,
        )

    async def setup_hook(self) -> None:
        nodes = [wavelink.Node(uri="http://0.0.0.0:2333", password=LAVALINK_PASS)]
        await wavelink.Pool.connect(nodes=nodes, client=self, cache_capacity=None)

    async def on_ready(self) -> None:
        self.channels: dict = {ch.name: (ch.id, ch) for ch in self.get_all_channels()}
        self.members = {mem.id: mem.name for mem in self.get_all_members()}
        self.home_channel = self.get_channel(self.channels["bot_talk"][1])
        logging.info(f"Logged in: {self.user} - ID: {self.user.id}")  # type:ignore
        logging.info(f"Home channel: {self.home_channel}")

    async def on_wavelink_node_ready(
        self, payload: wavelink.NodeReadyEventPayload
    ) -> None:
        logging.info(
            f"Wavelink Node connected: {payload.node!r} | Resumed: {payload.resumed}"
        )

    async def on_wavelink_track_start(
        self, payload: wavelink.TrackStartEventPayload
    ) -> None:
        player: wavelink.Player | None = payload.player
        if not player:
            logging.warning("Track-start event received without a player.")
            return

        original: wavelink.Playable | None = payload.original
        track: wavelink.Playable = payload.track
        embed: discord.Embed = discord.Embed(title="Now Playing")

        if track.uri and track.source:
            embed.description = (
                f"[*{track.title}* by **{track.author}**]({track.uri}) "
                f"from **{track.source.title()}**"
            )
        else:
            embed.description = f"*{track.title}* by **{track.author}**"

        if track.artwork:
            embed.set_image(url=track.artwork)

        if original and original.recommended:
            embed.description += (
                f"\n\nThis track was recommended by {track.source.title()}."
            )
            logging.info(
                f"Track recommended:\nOriginal: {original} - {original!r}\n"
                f"Original Title: {original.title}"
            )

        if track.album.name:
            embed.add_field(name="Album", value=track.album.name)

        if track.preview_url:
            embed.add_field(name="Link", value=track.preview_url)

        logging.info(f"Track started: {track!r}")
        await player.home.send(embed=embed)  # type:ignore
