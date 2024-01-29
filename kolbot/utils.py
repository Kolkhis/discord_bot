""" Helper functions for the bot """

import wavelink


async def get_current_queue(player: wavelink.Player) -> str | None:
    if not player:
        return None
    current_queue = {
        song.position: f"[*{song.title}* by **{song.author}**]({song.uri})"
        for song in player.queue
    }
    embed_string = (
        f"* Now Playing: [*{player.current.title}* by **{player.current}**]({player.current.uri})\n"
        if player.current
        else ""
    )
    for pos, song in current_queue.items():
        if pos == 0:
            embed_string += f"* Up Next: {song}"
            continue
        embed_string += f"\n* {pos}: {song}"
    return embed_string




