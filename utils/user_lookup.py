import discord
from typing import Optional

from bot import discord_bot

def name_for(
    user_id: int,
    *,
    guild: Optional[discord.Guild] = None,
) -> Optional[str]:
    """
    Resolve a Discord user-ID to a displayable name without extra API calls.

    • If a guild is supplied, return the nickname (`display_name`) there.
    • Else fall back to the global username (`user.name`).
    • Returns user_id if the ID is totally unknown to the bot cache.
    """
    if guild:
        member = guild.get_member(user_id)        # cache-only
        if member:
            return member.display_name

    user = discord_bot.get_user(user_id)                  # cache-only
    if user:
        return user.name

    return user_id
