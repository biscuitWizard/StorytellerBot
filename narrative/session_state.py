from typing import Optional, Dict, List
from pydantic import BaseModel, Field
from tinydb import Query

from narrative.models import Character, DatabaseModel, Narrative, Message, Scene
from db import db


class PoseRoundInfo(BaseModel):
  waiting_for_users: List[int] = Field(default_factory=list)
  # Characters that are not allowed to pose this round.
  character_blacklist: List[str] = Field(default_factory=list)
  

class SessionModel(DatabaseModel):
  channel_id: int

  narratives: List[str] = Field(default_factory=list)
  active_narrative_id: Optional[str] = None
  round: Optional[PoseRoundInfo] = None


class SessionState(SessionModel):
  last_bot_message: Optional[Message] = None
  status_message: Optional[Message] = None

  def active_scene(self) -> Optional[Scene]:
    if not self.active_narrative_id:
      return None
    narrative = db.get_by_id(Narrative, self.active_narrative_id)
    if not narrative.active_scene_id:
      return None
    return db.get_by_id(Scene, narrative.active_scene_id)
  
  def get_user_character(self, user_id) -> Optional[Character]:
    scene = self.active_scene()
    if not scene:
      return None
    return next((c for c in scene.characters if c.played_by == user_id), None)
  
  def get_character(self, name_or_id) -> Optional[Character]:
    scene = self.active_scene()
    if not scene:
      return None
    return next((c for c in scene.characters if c.template_id == name_or_id or c.name == name_or_id), None)
     

# Helper to get session per channel or DM
def get_session(channel_id) -> SessionModel:
  
  # Okay we need to maybe pull from storage?
  Q = Query()
  doc = db.tables["sessions"].get(Q.channel_id == channel_id)
  if doc:
    session = SessionState(**doc)
    return session
  
  # Nope this is a new session
  session = SessionState(channel_id=channel_id)
  # Create a default narrative
  narrative = Narrative(name="Default Narrative")
  # Also a default scene
  scene = Scene(name="New Scene", current_setting=None)

  session.narratives.append(narrative.id)
  session.active_narrative_id = narrative.id
  narrative.scenes.append(scene.id)
  narrative.active_scene_id = scene.id
  
  # Now persist everything
  db.insert(session)
  db.insert(narrative)
  db.insert(scene)

  return session