from discord import app_commands, Interaction
from discord.ext import commands
from db import db

from messages import character_embed
from narrative.models import Character, CharacterTemplate
from narrative.session_state import get_session

class CharacterCommands(app_commands.Group):
  @app_commands.command(name="add", description="Add a new character")
  async def add(self, interaction: Interaction, name: str):
    db.insert(CharacterTemplate(name=name, creator_id=interaction.user.id, creator_session_id=interaction.channel.id))
    await interaction.response.send_message(f"✅ Character **{name}** added.", ephemeral=True)

  @app_commands.command(name="info", description="View info of a character")
  async def info(self, interaction: Interaction, name_or_id: str):
    session = get_session(interaction.channel_id)
    char = session.get_character(name_or_id)
    if not char:
       # This can happen if we're switching to a character for the first time in a scene.
      char = db.get_character_template_by_id_or_name(interaction.user.id, name_or_id)
      if not char:
        await interaction.response.send_message(f"❌ Character **{name_or_id}** not found.", ephemeral=True)
        return
    await interaction.response.send_message(embed=character_embed(char), ephemeral=True)

  @app_commands.command(name="list", description="List all characters")
  async def list(self, interaction: Interaction):
    chars = db.get_available_characters(interaction.user.id)
    if not chars:
      await interaction.response.send_message("No characters found.", ephemeral=True)
    else:
      names = "\n".join(f"[{c.id}] - {c.name}" for c in chars)
      await interaction.response.send_message(f"**Characters:**\n{names}", ephemeral=True)

@app_commands.command(name="switch", description="Switches the current active character you're playing.")
async def switch_character(interaction: Interaction, name_or_id: str):
  session = get_session(interaction.channel_id)
  char = session.get_character(name_or_id)
  if not char:
    # This can happen if we're switching to a character for the first time in a scene.
    char = db.get_character_template_by_id_or_name(interaction.user.id, name_or_id)
    if not char:
      await interaction.response.send_message(f"❌ Character **{name_or_id}** not found.", ephemeral=True)
      return
    # We just added a new character, so we need to create a new character instance
    char = Character(template_id=char.id)
  session = get_session(interaction.channel.id)
  char.played_by = interaction.user.id
  active_scene = session.active_scene()
  active_scene.characters.append(char)
  # Save the scene
  db.update(active_scene)
  await interaction.response.send_message(f"Character **{char.name}** is now being played by **{interaction.user.display_name}**.", ephemeral=True)

async def setup(bot: commands.Bot):
    bot.tree.add_command(CharacterCommands(name="character"), guild=None)
    bot.tree.add_command(switch_character, guild=None)
    