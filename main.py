import os
import asyncio
import discord
import wavelink
from typing import cast
from discord.ext import commands
from bot import Bot


BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot: Bot = Bot()


@bot.command(aliases=["p", "add", "a", "addsong"])
async def play(ctx: commands.Context, *, query: str) -> None:
    """`:play (URL or search)` - Play song/playlist URL, or search for it\n"""
    if not ctx.guild:
        return
    player: wavelink.Player
    player = cast(wavelink.Player, ctx.voice_client)  # type: ignore
    if not player:
        try:
            player = await ctx.author.voice.channel.connect(cls=wavelink.Player)  # type: ignore
        except AttributeError:
            await ctx.send("Please join a voice channel first before using this command.")
            return
        except discord.ClientException:
            await ctx.send("I was unable to join this voice channel. Please try again.")
            return

    # enabled =  play songs and fetch recommendations
    # partial =  play songs, but don't fetch recommendations
    # disabled = do nothing
    player.autoplay = wavelink.AutoPlayMode.enabled

    # Lock the player to this channel
    if not hasattr(player, "home"):
        player.home = ctx.channel
    elif player.home != ctx.channel:
        await ctx.send(f"I'm already locked to {player.home.mention}.")
        return

    # fetch Tracks and Playlists
    # If spotify is enabled (LavaSrc), fetch Spotify tracks if it's a URL
    # use YouTube for regular searches (non-urls)
    try:
        tracks: wavelink.Search = await wavelink.Playable.search(query)
    except wavelink.LavalinkLoadException as e:
        if e.error == "The playlist does not exist.":
            new_query = query.split("&")[0]
            tracks: wavelink.Search = await wavelink.Playable.search(new_query)
        else:
            raise e

    if not tracks:
        await ctx.send(
            f"Sorry {ctx.author.mention}, I couldn't find any tracks that match "
            f'"{query}".\nTry again with a different query.'
        )
        return

    if isinstance(tracks, wavelink.Playlist):
        added: int = await player.queue.put_wait(tracks)
        await ctx.send(f"Added the playlist **{tracks.name}** ({added} songs) to the queue.")
    else:
        track: wavelink.Playable = tracks[0]
        await player.queue.put_wait(track)
        await ctx.send(f"Added **`{track}`** to the queue.")

    if not player.playing:
        await player.play(player.queue.get(), volume=30)

    if player and player.paused:
        await player.pause(False)
        await ctx.message.add_reaction("\u2705")

    try:
        await ctx.message.delete()
    except discord.HTTPException:
        pass


@bot.command(aliases=["s", "sk", "next", "n"])
async def skip(ctx: commands.Context) -> None:
    """`:skip` - Skip the current song."""
    player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
    if not player:
        return
    await player.skip(force=True)
    await ctx.message.add_reaction("\u2705")


@bot.command(name="toggle", aliases=["pause", "resume", "stop", "start", "t", "⏹️"])
async def pause_resume(ctx: commands.Context) -> None:
    """`:pause` / `:resume` - Pause or resume playback."""
    player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
    if not player:
        await ctx.send("Not connected to a voice channel.")
        return
    await player.pause(not player.paused)
    await ctx.message.add_reaction("\u2705")


@bot.command(name="volume", aliases=["vol", "v"])
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


@bot.command(name="disconnect", aliases=["dc", "quit", "exit", "q"])
async def disconnect(ctx: commands.Context) -> None:
    """`:quit` / `:dc` / `:exit` - Disconnect the player."""
    player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
    if not player:
        return
    await player.disconnect()
    await ctx.message.add_reaction("\u2705")


@bot.command(name="cmd", aliases=["commands", "cmds", "h", "man"])
async def cmd(ctx: commands.Context) -> None:
    """`:cmd` / `:h` - Get help: Display a list of commands."""
    # player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
    author: str = ctx.author.name
    embed: discord.Embed = discord.Embed(title="Help")
    embed.description = f"""
        SUP {author}, I'm a str8 up badass music bot. Here are my commands:\n
        * `:commands` - Display this help message
            \t* Aliases - `:h`, `:cmd`, `:cmds`, `:man`\n
        * `:play (URL or search)`- Play the song/playlist at the given URL, or search for it
            \t* Aliases - `:p`, `:add`, `:a`\n
        * `:volume (0-50)` - Change the volume of the player
            \t* Aliases - `:vol`\n
        * `:pause` - Pause the music player 
            \t* Aliases - `:stop`, `:toggle`, `:t`\n
        * `:resume` - Resume the music player
            \t* Aliases - `:start`, `:toggle`, `:t`\n
        * `:skip` - Skip the current song
            \t* Aliases - `:s`, `:sk`, `:next`, `:n`\n
        * `:autoplay (on/off)` - Toggle autoplay
            \t* Aliases - `:ap`, `:auto`, `:au`\n
        * `:queue` - Show the current queue
            \t* Aliases - `:vq`, `:list`, `:songs`, `:playlist`\n
        * `:quit` - Disconnect the bot from the voice channel
            \t* Aliases - `:q`, `:disconnect`, `:dc`\n
    """
    await ctx.message.add_reaction("🙃")
    await ctx.send(embed=embed)


@bot.command(name="autoplay", aliases=["ap", "auto", "au"])
async def toggle_autoplay(ctx: commands.Context, value: str | None = None) -> None:
    """`:autoplay (on/off)` / `:ap (on/off)` - Toggle autoplay."""
    player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
    if not value or value.strip() == '':
        values = {
            "on": wavelink.AutoPlayMode.enabled.value,          # 0
            "off": wavelink.AutoPlayMode.partial.value,         # 1
            "disabled": wavelink.AutoPlayMode.disabled.value,   # 2
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
        await ctx.message.add_reaction(u"🙃")
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


# Add command: vq or q: view the queue
@bot.command(name="queue", aliases=["vq", "list", "songs", "playlist"])
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
    embed = discord.Embed(title="Current Queue", description=f"**{player.queue!r}**")
    await ctx.send(embed=embed)

@bot.command(name="state", aliases=["st", "status", "getstate"])
async def get_state(ctx: commands.Context) -> None:
    player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
    if not player:
        await ctx.send("Not connected to a voice channel.")
        return
    is_paused: bool = player.paused
    playing_track: bool = player.playing
    channel: str = player.channel.name
    embed = discord.Embed(title="Current State")
    embed.description = f"Paused:  {is_paused}\n"\
                        f"Playing: {playing_track}\n"\
                        f"Channel: {channel}"
    await ctx.send(embed=embed)

    
        

async def main() -> None:
    async with bot:
        if BOT_TOKEN:
            await bot.start(BOT_TOKEN)
        else:
            raise Exception("No bot token provided.")


if __name__ == "__main__":
    asyncio.run(main())
