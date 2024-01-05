import datetime
import contextlib
import io
import os
import asyncio
import discord
import wavelink
from typing import cast
from discord.ext import commands
from bot import Bot
import logging

bot: Bot = Bot()

# TODO: Link to YT Music instead of YT

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
    "debug": ["run", "exec", "x"],
    "owner": ["own", "admin", "adm", "administrator"],
    "move": ["mv", "change", "switch", "hop"],
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
    player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
    if not player:
        try:
            player = await ctx.author.voice.channel.connect(  # type:ignore
                cls=wavelink.Player
            )
        except AttributeError:
            await ctx.send("Join a voice channel before using this command.")
            return
        except discord.ClientException:
            await ctx.send(
                f"{ctx.author.mention} I was unable to join your voice channel. Please try again."
            )
            return

    if len(player.channel.members) == 1:
        await player.disconnect()
        await ctx.send("Disconnected: I was alone in the voice channel.")
        return

    if not hasattr(player, "home"):
        player.home = ctx.channel  # type:ignore
    elif player.home != ctx.channel:  # type:ignore
        await ctx.send(
            f"I'm already in a channel: {player.home.mention}."  # type:ignore
        )
        return

    # Get tracks and playlists
    # If spotify is enabled (LavaSrc), get Spotify tracks if it's a URL
    # use YouTube for regular searches (non-urls)
    player.autoplay = wavelink.AutoPlayMode.enabled
    try:
        tracks: wavelink.Search = await wavelink.Playable.search(query)
    except wavelink.LavalinkLoadException as e:
        logging.warn(
            f"""Encountered LavalinkLoadException.\n
                     Cause: {e.cause}\n
                     Error: {e.error}\n
                     Severity: {e.severity}\n
                     Args: {e.args}\n
                     Full Error:{e}"""
        )
        if e.error == "The playlist does not exist.":
            new_query: str = query.split("&")[0]
            await ctx.send(f"Couldn't find that playlist. Searching for: {new_query}")
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
    finally:
        tracks = tracks if tracks else []  # type:ignore

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

    # TODO: Add check if the bot is alone in the voice channel

    try:
        await ctx.message.delete()
    except discord.HTTPException:
        pass


@bot.command(name="move", aliases=CMD_ALIASES["move"])
async def move(ctx: commands.Context, *, channel: str) -> None:
    """Change the channel of the bot."""
    player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
    if not player:
        try:
            # player = await ctx.author.voice.channel.connect(  # type:ignore
            #     cls=wavelink.Player
            # )
            if ctx.guild:
                player = await discord.utils.get(
                    ctx.guild.channels, name=channel
                ).connect(cls=wavelink.Player)
        except AttributeError:
            await ctx.send("Join a voice channel before using this command.")
            return
        except discord.ClientException:
            await ctx.send(
                f"{ctx.author.mention} I was unable to join your voice channel. Please try again."
            )
            return


@bot.command(aliases=CMD_ALIASES["skip"])
async def skip(ctx: commands.Context) -> None:
    """`:skip` - Skip the current song."""
    player: wavelink.Player
    if not (player := cast(wavelink.Player, ctx.voice_client)):
        return
    await player.skip(force=True)
    await ctx.message.add_reaction("\u2705")


@bot.command(name="toggle", aliases=CMD_ALIASES["pause_resume"])
async def pause_resume(ctx: commands.Context) -> None:
    """`:pause` / `:resume` - Pause or resume playback."""
    player: wavelink.Player
    if not (player := cast(wavelink.Player, ctx.voice_client)):
        await ctx.send("Not connected to a voice channel.")
        return
    await player.pause(not player.paused)
    await ctx.send("Playback paused." if player.paused else "Playback resumed.")
    await ctx.message.add_reaction("\u2705")


@bot.command(name="volume", aliases=CMD_ALIASES["volume"])
async def volume(ctx: commands.Context, value: int | None = None) -> None:
    """`:volume (0-50)` / `:vol` - Change the volume of the player."""
    player: wavelink.Player
    if not (player := cast(wavelink.Player, ctx.voice_client)):
        await ctx.send("Not connected to a voice channel.")
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
    if not (player := cast(wavelink.Player, ctx.voice_client)):
        return
    await player.disconnect()
    await ctx.message.add_reaction("\u2705")


@bot.command(name="help", aliases=CMD_ALIASES["help"])
async def help(ctx: commands.Context) -> None:
    """`:cmd` / `:h` - Get help: Display a list of commands."""
    embed: discord.Embed = discord.Embed(title="Help")
    prefix_msg: str = (
        f"* Bot prefix(es): `{bot.prefixes!r}`\n\t* Usage: `<prefix><command>`\n"
    )
    embed.add_field(name="Bot Prefix", value=prefix_msg, inline=False)
    for cmd, doc in DOCS.items():
        cmd_alias: str = "\t* Aliases - "
        for alias in CMD_ALIASES[cmd]:
            cmd_alias += (
                f"`{alias}`, " if alias != CMD_ALIASES[cmd][-1] else f"`{alias}`\n"
            )
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
            **Note**: `disabled` will disable playlists from autoplaying.\n
            `on`: Play songs and fetch recommendations \n
            `off`: Play songs, but don't fetch recommendations \n
            `disabled`: Don't autoplay anything, even playlists. \n
            """
        else:
            embed.description = f"""
            Possible values: `on`, `off`, `disabled`\n
            **Note**: `disabled` will disable playlists from autoplaying.\n
            `on`: Play songs and fetch recommendations (0)\n
            `off`: Play songs, but don't fetch recommendations (1)\n
            `disabled`: Don't autoplay anything, even playlists. (2)\n
            """
        embed.set_footer(text="Toggle autoplay with :autoplay (on/off)")
        await ctx.message.add_reaction("🙃")
        await ctx.send(embed=embed)
        return
    if not (player := cast(wavelink.Player, ctx.voice_client)):
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
    player: wavelink.Player
    if not (player := cast(wavelink.Player, ctx.voice_client)):
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
    if not (player := cast(wavelink.Player, ctx.voice_client)):
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


@bot.command(name="debug", aliases=CMD_ALIASES["debug"])
async def debug(ctx: commands.Context, *, value: str | None) -> None:
    player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
    if not player:
        await ctx.message.add_reaction("⏹")
    if str(ctx.author.id) == os.environ.get("OWNER_ID") and bot.is_owner(ctx.author):
        await ctx.message.add_reaction("🙃")
        if value is None:
            await ctx.send(f"{bot.is_owner} No input provided.")
            return
    else:
        await ctx.message.add_reaction("🚫")
        await ctx.send(
            f"{ctx.author.mention} You don't have permission to use this command."
        )
        return
    value = str(value)
    # Redirecting stdout to capture the output of exec/eval
    stdout = io.StringIO()
    try:
        with contextlib.redirect_stdout(stdout):
            # Using eval for expressions that return a value
            try:
                result = eval(value)
                if result is not None:
                    print(result)
            except:
                # Using exec for other cases
                exec(value)
        output = stdout.getvalue()
        await ctx.send(f"```py\n{output}\n```")
    except Exception as e:
        await ctx.send(f"```py\nError: {e}\n```")


@bot.command(name="owner", aliases=CMD_ALIASES["owner"])
async def owner(ctx: commands.Context) -> None:
    msg: str = ""
    if str(ctx.author.id) == os.environ.get("OWNER_ID") == str(bot.owner_id):
        msg += f"{ctx.author.mention} Owner IDs match.\n"
        if bot.is_owner(ctx.author):
            msg += f"bot.is_owner({ctx.author.global_name}) returns True.\n"
    embed: discord.Embed = discord.Embed(
        title="Owner Check", description=msg, timestamp=datetime.datetime.now()
    )
    await ctx.send(embed=embed)


async def main() -> None:
    async with bot:
        if BOT_TOKEN:
            await bot.start(BOT_TOKEN)
        else:
            raise Exception("No bot token provided.")


if __name__ == "__main__":
    asyncio.run(main())
