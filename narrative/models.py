from functools import cached_property
import uuid
from datetime import datetime
from typing import Any, List, Optional, Dict
from pydantic import BaseModel, Field


class DatabaseModel(BaseModel):
  id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class Message(BaseModel):
  character_id: str
  character_name: str
  content: str
  internal_thought: Optional[str] = None
  is_player: bool = False


class CharacterTemplate(DatabaseModel):
  creator_session_id: int
  creator_id: int
  name: str
  physical_description: Optional[str] = None
  author_notes: Optional[str] = None
  personality: Optional[str] = None
  display_picture: Optional[str] = None


class Character(DatabaseModel):
  template_id: str
  
  played_by: Optional[int] = None
  # talkativeness: int = 0.0
  character_data: Dict[str, str] = Field(default_factory=dict)

  # lazy-load; cached after first use
  @cached_property
  def _template(self) -> CharacterTemplate | None:
    from db import db
    return db.get_by_id(CharacterTemplate, self.template_id)

  def __getattr__(self, item: str) -> Any:           # called *after* normal lookup
    if item in CharacterTemplate.model_fields:     # pydantic-v2 attribute
      tmpl = self._template
      if tmpl:
        return getattr(tmpl, item)
    raise AttributeError(item)     

class Setting(DatabaseModel):
  name: str
  description: str
  author_notes: Optional[str] = None
  picture: Optional[str] = None


class Scene(DatabaseModel):
  name: str
  characters: List[Character] = Field(default_factory=list)
  messages: List[Message] = Field(default_factory=list)
  # start_date: datetime = Field(default_factory=datetime.utcnow)
  current_setting: Optional[Setting] = None


class Narrative(DatabaseModel):
  name: str
  scenes: List[str] = Field(default_factory=list)
  settings: List[str] = Field(default_factory=list)

  active_scene_id: Optional[str] = None
