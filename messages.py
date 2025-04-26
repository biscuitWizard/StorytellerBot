import discord
from narrative.models import CharacterTemplate, Message, Scene
from narrative.session_state import SessionState, get_session


def scene_embed(session: SessionState, scene: Scene, *, color: int = 0x5865F2) -> discord.Embed:
  from utils.user_lookup import name_for

  embed = discord.Embed(
    title=scene.id,
    description= ":green_circle: Active" if session.round else ":red_circle: Inactive", 
    color=color
  )

  if scene.characters:
    characters = ""
    for character in scene.characters:
      characters += f"- **{character.name}**"

      if character.played_by:
        characters += f" (Played by {name_for(character.played_by)})\n"
      else:
        characters += " (AI)\n"
    embed.add_field(name="Characters", value=characters, inline=True)

  return embed


def character_embed(char: CharacterTemplate, *, color: int = 0x5865F2) -> discord.Embed:
    """
    Convert a Character instance to a Discord Embed.
    """
    embed = discord.Embed(
      title=char.name,
      color=color
    )

    # Display picture
    if char.display_picture:
      pass
    else:
      embed.set_thumbnail(url="https://cataas.com/cat")

    if char.physical_description:
      embed.add_field(name="Physical Description", value=char.physical_description[:1024], inline=False)
    if char.personality:
      embed.add_field(name="Personality", value=char.personality[:1024], inline=False)

    # Generate character data
    # for key, value in char.character_data.items():
    #   embed.add_field(name=key, value=value, Inline=True)

    # footer / timestamp for freshness
    embed.set_footer(text="Character Sheet")
    embed.timestamp = discord.utils.utcnow()

    return embed

async def send_emote(interaction: discord.Interaction, message: Message):
  embed = discord.Embed(
    title=message.character_name,
    # description=message.content
    # description=f"```{message.content}```"
  )

  embed.add_field(name="Content", value=f"{message.content}", inline=False)

  # embed.set_thumbnail(url="https://cataas.com/cat")
  return await interaction.response.send_message(embed=embed, ephemeral=False)

async def send(channel_id: int, text: any):
  """
  Send a plain message to the channel designated by channel_id.
  Uses the cache when possible; falls back to a REST fetch.
  """

  from bot import discord_bot
  # 1) Try the gateway cache — no API call, instant.
  channel = discord_bot.get_channel(channel_id)

  # 2) Cache miss?  Do a REST call (one request, rate-limited).
  if channel is None:
    channel = await discord_bot.fetch_channel(channel_id)   # raises NotFound if invalid
    
  session = get_session(channel_id)
  async def clear_status():
    # delete old status if present
    if session.status_message:
      try:
        await session.status_message.delete()
        session.status_message = None
      except:
        pass

  # Helper to set a new status
  async def set_status(content: str):
    # delete old status if present
    await clear_status()
    session.status_message = await channel.send(content)

  # 3) Send the message.
  msg = await channel.send(text)

  # Move our status message back to the bottom
  if session.status_message:
    set_status(session.status_message.content)

  return msg
  