from typing import Optional, Type, TypeVar, List
from tinydb import TinyDB, Query
from narrative.models import Character, CharacterTemplate, DatabaseModel

T = TypeVar('T', bound=DatabaseModel)

class DatabaseProvider:
  def __init__(self):
    self.tables = {
      "characters": TinyDB('data/characters.json'),
      "scenes": TinyDB('data/scenes.json'),
      "settings": TinyDB('data/settings.json'),
      "sessions": TinyDB('data/sessions.json'),
      "narratives": TinyDB('data/narratives.json')
    }        

  def _get_table(self, model_cls: Type[T]) -> TinyDB:
    match model_cls.__name__:
      case "CharacterTemplate":
        return self.tables["characters"]
      case "Scene":
        return self.tables["scenes"]
      case "Setting":
        return self.tables["settings"]
      case "SessionModel":
        return self.tables["sessions"]
      case "SessionState":
        return self.tables["sessions"]
      case "Narrative":
        return self.tables["narratives"]
    raise ValueError(f"No table registered for model: {model_cls.__name__}")

  def insert(self, model: T) -> str:
    table = self._get_table(type(model))
    table.insert(model.model_dump())
    return model.id
  
  def get_available_characters(self, user_id: int) -> List[T]:
    Q = Query()
    return [CharacterTemplate(**doc) for doc in self.tables["characters"].search((Q.creator_id == user_id))]
  
  def get_character_template_by_id_or_name(self, user_id: int, user_name_id: str) -> Optional[T]:
    Q = Query()
    doc = self.tables["characters"].get((Q.creator_id == user_id) & ((Q.id == user_name_id) | (Q.name == user_name_id)))
    return CharacterTemplate(**doc) if doc else None

  def get_by_id(self, model_cls: Type[T], uuid_val: str) -> Optional[T]:
    Q = Query()
    for _, table in self.tables.items():
      doc = table.get(Q.id == uuid_val)
      if doc:
        return model_cls(**doc)
  
  def update(self, model: T) -> bool:
    Q = Query()
    table = self._get_table(type(model))
    return bool(table.update(model.model_dump(), Q.id == model.id))

  def insert(self, model: T) -> int:
    table = self._get_table(type(model))
    table.insert(model.model_dump())
    return model.id

db = DatabaseProvider()