import random
import re
from typing import List
from discord import Interaction, app_commands
from discord.ext import commands
import yaml
from client import AgentClient
from db import db
from narrative.models import Character, Message, Scene
from narrative.session_state import PoseRoundInfo, SessionModel, get_session
from template import Template

with open("model.yml", "r") as f:
    cfg = yaml.safe_load(f)
template = Template.from_file("default_template.txt")

WORD_RE = re.compile(r"\w+")
def activate_natural_order(scene: Scene, last_messages: List[Message]) -> List[Character]:
  """
  Decide which characters in *scene* will speak this turn.

  The function returns a list of **Character** objects, in the order they
  should speak.
  """
  def _extract_all_words(text: str) -> List[str]:
    """Split text into lower-case words (same rule the JS used)."""
    return WORD_RE.findall(text.lower())
  
  characters = []
  for member in scene.characters:        # or whatever list of Character objects you have
    if member.played_by is None:
        characters.append(member)

  if not characters:        # nothing to do
      return []

  # Convenience tables
  activated: list[Character] = []     # avatar IDs chosen to speak
  chatty: list[Character] = []        # avatars with talkativeness > 0

  # ──────────────────────────────────────────────────────────────────────────
  # 2.  Mention-based activation 
  # ──────────────────────────────────────────────────────────────────────────
  for message in last_messages:
    #  if not message.is_player:
    #     continue
     input_text = message.content
     for word in _extract_all_words(input_text):
        for char in characters:
          if char.id == message.character_id:
            continue # Don't check NPC messages to see if they refer to themselves
          if word in _extract_all_words(char.name):
            activated.append(char)
            break
      

  # ──────────────────────────────────────────────────────────────────────────
  # 3.  Talkativeness-based activation  (each member gets a random roll)
  # ──────────────────────────────────────────────────────────────────────────
  for char in random.sample(list(characters), k=len(characters)):  # shuffled copy
      talk = (
          float(char.talkativeness)
          if getattr(char, "talkativeness", None) is not None
          else 0.5
      )
      if talk >= random.random():
          activated.append(char)
      if talk > 0:
          chatty.append(char)

  # ──────────────────────────────────────────────────────────────────────────
  # 4.  Fallback – pick one random speaker if still nobody activated
  # ──────────────────────────────────────────────────────────────────────────
  pool = chatty if chatty else list(characters)
  retries = 0
  while not activated and retries < len(pool):
      activated.append(random.choice(pool))
      retries += 1

  # ──────────────────────────────────────────────────────────────────────────
  # 5.  Remove duplicates (preserve order) and map back to Character objects
  # ──────────────────────────────────────────────────────────────────────────
  seen = set()
  unique_characters: list[Character] = []
  for a in activated:
      if a.id not in seen:
          unique_characters.append(a)
          seen.add(a.id)

  return unique_characters


@app_commands.command(
    name="emote",
    description="Do an action as your character."
)
# @app_commands.describe(
#     id_or_name="ID or name of the record",
#     field="Field to change (must be on the whitelist)",
#     value="New value"
# )
async def emote(
  interaction: Interaction,
  pose: str
):
  session = get_session(interaction.channel_id)
  if not session.round:
      return
  
  # We are in a running scene and someone may have just posed.
  from messages import send_emote
  char = session.get_user_character(interaction.user.id)
  if not char:
    print(f"{interaction.user.name} does not currently have a character; ignoring...")
    return # They don't have a character; ignore them
  
  if interaction.user.id not in session.round.waiting_for_users:
      print(f"{interaction.user.name} already has made a pose this order; ignoring...")
      return
  
  active_scene = session.active_scene()
  new_message = Message(character_id=char.id, character_name=char.name, content=pose, is_player=True)
  active_scene.messages.append(new_message)
  await send_emote(interaction, new_message)
  session.round.waiting_for_users.remove(interaction.user.id)

  db.update(active_scene)

  if session.round.waiting_for_users:
    return
  
  # Time for the AIs to respond
  def last_round(messages: List[Message]) -> List[Message]:
    """
    Return the tail of *messages* consisting of:
      • the most-recent contiguous block of player messages (is_player == True)
      • followed by any contiguous NPC messages after them (is_player == False)
    Stop before the next earlier player message.

    The returned list keeps chronological order.
    """
    collected: List[Message] = []
    seen_npc = False            # flips to True once we hit the first NPC line

    # walk backward through the log
    for msg in reversed(messages):
      if msg.is_player:
        if seen_npc:        # we hit an earlier player turn → done
          break
        collected.append(msg)
      else:                   # NPC / system message
        seen_npc = True
        collected.append(msg)
    collected.reverse()         # restore chronological order
    return collected
  
  client = AgentClient("http://192.168.1.50:5000", retries=5, backoff_factor=0.5)
  for character in activate_natural_order(active_scene, last_round(active_scene.messages)):
    # await set_status('```Generating a response...```')
    users = "Lily"
    prompt = template.render({
      "characters": active_scene.characters,
      "acting_character": character,
      "messages": active_scene.messages,
      "users": users
    })

    stopping_strings = ['###', '\n***', '<END_POSE>', '\n\n']
    for c in active_scene.characters:
      stopping_strings.append(f'{c.name}:')
    print(prompt)

    response = client.post('/v1/completions', headers={"x-api-key": '<your token here>'}, json={
      "prompt": prompt,
      "stopping_strings": stopping_strings,
      "model": "Eurydice-24b-v2",
      **cfg["generation"]
    })

    full_text = trim_pose(response['choices'][0]['text'])
    message = Message(character_id=character.id, character_name=character.name, content=full_text, is_player=False)
    active_scene.messages.append(message)
    db.update(active_scene)
    session.last_bot_message = send_emote(interaction, message)
  
  # We're done responding so now we can reset the new pose round
  session.round = PoseRoundInfo()
  for c in active_scene.characters:
    if c.played_by:
      session.round.waiting_for_users.append(c.played_by)
  db.update(SessionModel(**session.model_dump()))
  
  
async def setup(bot: commands.Bot):
  bot.tree.add_command(emote, guild=None)