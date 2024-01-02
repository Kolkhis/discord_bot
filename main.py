import datetime
import os
import asyncio
import discord
from discord.ext.commands.core import is_owner
import wavelink
from typing import cast
from discord.ext import commands
from bot import Bot
import logging

bot: Bot = Bot()
BOT_TOKEN = os.environ.get("BOT_TOKEN")

CMD_ALIASES = {
    "play": ["p", "add", "a", "addsong"],
    "pause_resume": ["pause", "unpause", "t", "stop", "start"],
    "skip": ["s", "sk", "next", "n"],
    "volume": ["vol", "v"],
    "queue": ["vq", "list", "ls", "songs", "playlist"],
    "state": ["st", "status", "getstate"],
    "autoplay": ["ap", "auto", "au"],
    "disconnect": ["dc", "quit", "exit", "q"],
    "help": ["cmd", "commands", "cmds", "h", "man", "docs"],
}

DOCS = {
    "play": f"* Plays a song or playlist from a given URL or search query.\n", 
    "pause_resume": f"* Pauses or resumes playback.\n", 
    "skip": f"* Skips the current song.\n", 
    "volume": f"* Changes the volume of the player (0-50).\n", 
    "queue": f"* Displays the current queue.\n", 
    "state": f"* Displays the current state of the player.\n", 
    "autoplay": f"* Toggles autoplay. Arguments: `on`/`off`/`disable`.\n", 
    "disconnect": f"* Disconnects the player from the voice channel.\n", 
    "help": f"* Displays this help message.\n", 
}


@bot.command(aliases=CMD_ALIASES["play"])
async def play(ctx: commands.Context, *, query: str) -> None:
    """`:play (URL or search)` - Play song/playlist URL, or search for it\n"""
    if not ctx.guild:
        return
    player: wavelink.Player
    player = cast(wavelink.Player, ctx.voice_client)
    if not player:
        try:
            player = await ctx.author.voice.channel.connect(cls=wavelink.Player)  # type:ignore
        except AttributeError:
            await ctx.send("Join a voice channel before using this command.")
            return
        except discord.ClientException:
            await ctx.send(
                f"{ctx.author.mention} I was unable to join your voice channel. Please try again."
            )
            return

    # enabled =  play songs and recommendations
    # partial =  play songs but don't play recommendations
    # disabled = do nothing
    player.autoplay = wavelink.AutoPlayMode.enabled

    # Lock the player to this channel
    if not hasattr(player, "home"):
        player.home = ctx.channel   # type:ignore
    elif player.home != ctx.channel: # type:ignore
        await ctx.send(f"I'm already locked to {player.home.mention}.") # type:ignore
        return

    # fetch Tracks and Playlists
    # If spotify is enabled (LavaSrc), fetch Spotify tracks if it's a URL
    # use YouTube for regular searches (non-urls)
    try:
        tracks: wavelink.Search = await wavelink.Playable.search(query)
    except wavelink.LavalinkLoadException as e:
        logging.warn(
            f"Encountered LavalinkLoadException.\n \
                     Cause: {e.cause}\n \
                     Error: {e.error}\n \
                     Severity: {e.severity}\n \
                     Args: {e.args}\n \
                     Full Error:{e}"
        )
        if e.error == "The playlist does not exist.":
            new_query: str = query.split("&")[0]
            tracks: wavelink.Search = await wavelink.Playable.search(new_query)
        else:
            logging.warn(f"Error while searching for tracks: {e}")
            await ctx.send("The playlist couldn't be loaded. Maybe it's private?")
            raise e
    except commands.errors.CommandInvokeError as e:
        logging.warn(f"%(filename)s: Encountered CommandInvokeError.\nArgs: {e.args}")
        try:
            new_query: str = query.split("&")[0]
            tracks: wavelink.Search = await wavelink.Playable.search(new_query)
        except Exception as e:
            logging.warn(f"Error while searching for tracks: {e}")
            await ctx.send("The playlist couldn't be loaded. Maybe it's private?")
    except Exception as e:
        logging.warn(f"Error while searching for tracks: {e}")
        await ctx.send("The playlist couldn't be loaded. Maybe it's private?")

    if not tracks:
        await ctx.send(
            f"Sorry {ctx.author.mention}, I couldn't find any tracks that match "
            f'"{query}".\nTry again with a different query.'
        )
        return

    if isinstance(tracks, wavelink.Playlist):
        added: int = await player.queue.put_wait(tracks)
        await ctx.send(
            f"{ctx.author.mention} added the playlist **{tracks.name}** ({added} songs) to the queue."
        )
    else:
        track: wavelink.Playable = tracks[0]
        await player.queue.put_wait(track)
        await ctx.send(f"{ctx.author.mention} Added **`{track}`** to the queue.")

    if not player.playing:
        await player.play(player.queue.get(), volume=30)

    if player and player.paused:
        await player.pause(False)
        await ctx.message.add_reaction("\u2705")

    try:
        await ctx.message.delete()
    except discord.HTTPException:
        pass


@bot.command(aliases=CMD_ALIASES["skip"])
async def skip(ctx: commands.Context) -> None:
    """`:skip` - Skip the current song."""
    player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
    if not player:
        return
    await player.skip(force=True)
    await ctx.message.add_reaction("\u2705")


@bot.command(name="toggle", aliases=CMD_ALIASES["pause_resume"])
async def pause_resume(ctx: commands.Context) -> None:
    """`:pause` / `:resume` - Pause or resume playback."""
    player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
    if not player:
        await ctx.send("Not connected to a voice channel.")
        return
    # msg: str = "Playback paused." if player.paused else "Playback resumed."
    await player.pause(not player.paused)
    await ctx.send("Playback paused." if player.paused else "Playback resumed.")
    await ctx.message.add_reaction("\u2705")


@bot.command(name="volume", aliases=CMD_ALIASES["volume"])
async def volume(ctx: commands.Context, value: int | None = None) -> None:
    """`:volume (0-50)` / `:vol` - Change the volume of the player."""
    player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
    if not player:
        return
    if bot.is_owner(ctx.author):
        match value:
            case None:
                await ctx.send(f"debug: Current volume: {player.volume}")
                return await ctx.message.add_reaction("🙃")
            case value if value <= 1000:
                await player.set_volume(value)
                await ctx.send(f"debug: Volume set to {player.volume}")
                return await ctx.message.add_reaction("🙃")
            case _:
                await ctx.send("debug: Enter a value between 1 and 1000.")
                return await ctx.message.add_reaction("🙃")
    match value:
        case None:
            await ctx.send(f"The current volume is {player.volume}")
        case value if value <= 50:
            await player.set_volume(value)
        case _:
            await ctx.send("Enter a value between 0 and 50")
        # await player.set_volume(value)
    await ctx.message.add_reaction("\u2705")


@bot.command(name="disconnect", aliases=CMD_ALIASES["disconnect"])
async def disconnect(ctx: commands.Context) -> None:
    """`:quit` / `:dc` / `:exit` - Disconnect the player from the voice channel. Clears queue."""
    player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
    if not player:
        return
    await player.disconnect()
    await ctx.message.add_reaction("\u2705")


@bot.command(name="help", aliases=CMD_ALIASES["help"])
async def help(ctx: commands.Context) -> None:
    """`:cmd` / `:h` - Get help: Display a list of commands."""
    embed: discord.Embed = discord.Embed(title="Help")
    prefix_msg: str = f"* Bot prefix(es): `{bot.prefixes!r}`\n\t* Usage: `<prefix><command>`\n"
    embed.add_field(name="Bot Prefix", value=prefix_msg, inline=False)
    for cmd, doc in DOCS.items():
        cmd_alias: str = '\t* Aliases - '
        for alias in CMD_ALIASES[cmd]:
            cmd_alias += f"`{alias}`, " if alias != CMD_ALIASES[cmd][-1] else f"`{alias}`\n"
        doc += cmd_alias
        embed.add_field(name=cmd, value=doc, inline=False)

    await ctx.message.add_reaction("🙃")
    await ctx.send(embed=embed)


@bot.command(name="autoplay", aliases=CMD_ALIASES["autoplay"])
async def toggle_autoplay(ctx: commands.Context, value: str | None = None) -> None:
    """`:autoplay (on/off)` / `:ap (on/off)` - Toggle autoplay."""
    player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
    if not value or value.strip() == "":
        values = {
            "on": wavelink.AutoPlayMode.enabled.value,  # 0
            "off": wavelink.AutoPlayMode.partial.value,  # 1
            "disabled": wavelink.AutoPlayMode.disabled.value,  # 2
        }
        embed: discord.Embed = discord.Embed(title="Autoplay")
        if player:
            embed.description = f"""
            Autoplay is currently set to {player.autoplay}\n
            Possible values: `on`, `off`, `disabled`\n
            **Note**: `disabled` will disable playlists from autoplaying.
            `on`: play songs and fetch recommendations
            `off`: play songs, but don't fetch recommendations
            `disabled`: Don't autoplay anything, even playlists.
            """
        else:
            embed.description = f"""
            Possible values: `on`, `off`, `disabled`\n
            **Note**: `disabled` will disable playlists from autoplaying.
            `on`: Play songs and fetch recommendations
            `off`: Play songs, but don't fetch recommendations
            `disabled`: Don't autoplay anything, even playlists.
            """
        embed.set_footer(text="Toggle autoplay with :autoplay (on/off)")
        await ctx.message.add_reaction("🙃")
        await ctx.send(embed=embed)
        return
    if not player:
        return
    match value:
        case "on":
            player.autoplay = wavelink.AutoPlayMode.enabled
        case "off":
            player.autoplay = wavelink.AutoPlayMode.partial
    await ctx.message.add_reaction("\u2705")


async def get_current_queue(player: wavelink.Player) -> str | None:
    if not player:
        return None
    current_queue = {
        song.position: f"[{song.title} by {song.author}]({song.uri})"
        for song in player.queue
    }

    embed_string = (
        f"* Now Playing: [{player.current.title} by {player.current}]({player.current.uri})\n"
        if player.current
        else ""
    )
    for pos, song in current_queue.items():
        if pos == 0:
            embed_string += f"* Up Next: {song}"
            continue
        embed_string += f"\n* {pos}: {song}"
    return embed_string


@bot.command(name="queue", aliases=CMD_ALIASES["queue"])
async def queue(ctx: commands.Context) -> None:
    """`:queue` - View the current queue."""
    player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
    if not player:
        await ctx.send("Not connected to a voice channel.")
        return
    if not player.queue:
        await ctx.send("The queue is currently empty.")
        return
    # await ctx.send(f"The current queue:\n{player.queue}")
    embed = discord.Embed(title="Current Queue", timestamp=datetime.datetime.now())

    embed_string = await get_current_queue(player)
    if embed_string:
        embed.description = (
            f"The current queue:\n\n{embed_string}"
            if embed_string
            else "Queue is empty"
        )
        await ctx.send(embed=embed)
    else:
        await ctx.send("The queue appears to be empty.")


@bot.command(name="state", aliases=CMD_ALIASES["state"])
async def get_state(ctx: commands.Context) -> None:
    player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
    if not player:
        await ctx.send("Not connected to a voice channel.")
        return
    is_paused: bool = player.paused
    playing_track: bool = player.playing
    channel: str = player.channel.name
    embed = discord.Embed(title="Current State", timestamp=datetime.datetime.now())
    embed.description = (
        f"Paused:  {is_paused}\n" f"Playing: {playing_track}\n" f"Channel: {channel}"
    )
    await ctx.send(embed=embed)

@bot.command(name='debug')
async def debug(ctx: commands.Context) -> None:
    if ctx.author.id == os.environ.get("OWNER_ID"):
        pass  # TODO: Eval

async def main() -> None:
    async with bot:
        if BOT_TOKEN:
            await bot.start(BOT_TOKEN)
        else:
            raise Exception("No bot token provided.")


if __name__ == "__main__":
    asyncio.run(main())
