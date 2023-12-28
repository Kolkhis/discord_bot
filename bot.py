#!/usr/bin/env python3
import os
import discord
import logging
import wavelink
from discord.ext import commands

LAVALINK_PASS = os.environ['LAVALINK_PASS']

class Bot(commands.Bot):
    def __init__(self) -> None:
        intents: discord.Intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix=":", intents=intents)
        logging.basicConfig(filename="./bot.log", level=logging.INFO)
        discord.utils.setup_logging(level=logging.INFO)

    async def setup_hook(self) -> None:
        nodes = [wavelink.Node(uri="http://0.0.0.0:2333", password=LAVALINK_PASS)]
        await wavelink.Pool.connect(nodes=nodes, client=self, cache_capacity=None)

    async def on_ready(self) -> None:
        logging.info(f"Logged in as: {self.user} | {self.user.id}")
        # logging.info(f"Guilds: {self.guilds.__str__}")

    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload) -> None:
        logging.info(f"Wavelink Node connected: {payload.node!r} | Resumed: {payload.resumed}")

    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload) -> None:
        player: wavelink.Player | None = payload.player
        if not player:
            logging.warning('Track-start event received without a player.')
            return

        original: wavelink.Playable | None = payload.original
        track: wavelink.Playable = payload.track

        embed: discord.Embed = discord.Embed(title="Now Playing")

        if track.uri and track.source:
            embed.description = f"[*{track.title}* by **{track.author}**]({track.uri}) "\
                                f"from **{track.source.title()}**"
        else:
            embed.description = f"*{track.title}* by **{track.author}**"

        if track.artwork:
            embed.set_image(url=track.artwork)

        if original and original.recommended:
            embed.description += f"\n\nThis track was recommended by {track.source.title()}."
            logging.info(f"Track recommended:\nOriginal: {original} - {original!r}\n"
                         f"Original Title: {original.title}")

        if track.album.name:
            embed.add_field(name="Album", value=track.album.name)

        if track.preview_url:
            embed.add_field(name="Link", value=track.preview_url)

        logging.info(f"Track started: {track!r}")
        await player.home.send(embed=embed)

