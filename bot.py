from typing import List, Sequence
import discord
import yaml
import re
import random
from db import db
from client import AgentClient
from discord.ext import commands

from narrative.session_state import PoseRoundInfo, SessionModel, get_session
from narrative.models import Character, Message, Scene
from commands import characters, general, roleplay, scene
from template import Template
from utils.text import trim_pose, chunk_by_words

class NymphoBot(commands.Bot):
  async def setup_hook(self):
    await characters.setup(self)
    await general.setup(self)
    await scene.setup(self)
    await roleplay.setup(self)

intents = discord.Intents.default()
intents.message_content = True
intents.dm_messages = True
intents.guild_messages = True
intents.messages = True
discord_bot = NymphoBot(command_prefix="!", intents=intents)

@discord_bot.event
async def on_ready():
    print(f'Bot connected as {discord_bot.user}')
    synced = await discord_bot.tree.sync()
    print(f"Synced {len(synced)} global commands")