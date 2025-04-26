from discord.ext import commands

from messages import scene_embed
from narrative.models import Character
from narrative.session_state import PoseRoundInfo, get_session

from discord import app_commands, Interaction
from discord.ext import commands
from db import db

class SceneCommands(app_commands.Group):
  @app_commands.command(name="info", description="Shows current scene information")
  async def info(self, interaction: Interaction):
    session = get_session(interaction.channel.id)
    scene = session.active_scene()
    await interaction.response.send_message(embed=scene_embed(session, scene), ephemeral=True)

  @app_commands.command(name="start", description="Starts recording for the scene")
  async def start(self, interaction: Interaction):
    session = get_session(interaction.channel.id)
    if session.round:
      await interaction.response.send_message(f"The scene is already running.", ephemeral=True)
      return

    session.round = PoseRoundInfo()
    for c in session.active_scene().characters:
      if c.played_by:
        session.round.waiting_for_users.append(c.played_by)
    db.update(session)
    await interaction.response.send_message(f"The scene is now running.")    

  @app_commands.command(name="stop", description="Stops recording the current scene")
  async def stop(self, interaction: Interaction):
    session = get_session(interaction.channel.id)
    if not session.round:
        await interaction.response.send_message(f"The scene is not currently running.", ephemeral=True)
        return

    session.round = None
    db.update(session)
    await interaction.response.send_message(f"The scene is now stopped.")

  @app_commands.command(name="add", description="Adds a character to the scene")
  async def add(self, interaction: Interaction, name_or_id: str):
    char_template = db.get_character_template_by_id_or_name(interaction.user.id, name_or_id)
    if not char_template:
      await interaction.response.send_message(f"❌ Character **{name_or_id}** not found.", ephemeral=True)
      return
    session = get_session(interaction.channel.id)
    active_scene = session.active_scene()
    if not active_scene:
      await interaction.response.send_message(f"❌ There is no currently active scene.", ephemeral=True)
      return
    # if char in active_scene.active_characters:
    #   await interaction.response.send_message(f"❌ Character **{char.name}** is already in the scene.", ephemeral=True)
    #   return
    char = Character(template_id=char_template.id)
    active_scene.characters.append(char)
    db.update(active_scene)
    await interaction.response.send_message(f"Added **{char_template.name}** to current scene.")


async def setup(bot: commands.Bot):
    bot.tree.add_command(SceneCommands(name="scene"), guild=None)