import re

def chunk_by_words(text: str, limit: int = 1700) -> list[str]:
  words = text.split()
  chunks = []
  current = []
  length = 0

  for w in words:
    # +1 for the space
    if length + len(w) + (1 if current else 0) > limit:
      chunks.append(" ".join(current))
      current = [w]
      length = len(w)
    else:
      current.append(w)
      length += len(w) + (1 if current[:-1] else 0)
  if current:
    chunks.append(" ".join(current))

  return chunks

def trim_pose(text: str) -> str:
  # Remove <POSE_END> and everything after (including any whitespace before it),
  # then strip remaining leading/trailing whitespace.
  trimmed = re.sub(r"\s*<POSE_END>.*$", "", text, flags=re.DOTALL)
  return trimmed.strip()