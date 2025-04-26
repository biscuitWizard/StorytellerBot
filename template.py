import re

class Template:
    """
    A simple template engine supporting:
      - {{ var }} interpolation (with dot notation, e.g. {{ user.name }})
      - {% if var %} ... {% endif %} conditional blocks (dot notation supported)
      - {% for item in list %} ... {% endfor %} loops
    """

    VAR_PATTERN = re.compile(r"\{\{\s*([\w\.]+)\s*\}\}")
    IF_PATTERN = re.compile(r"\{% if ([\w\.]+) %\}")
    ENDIF_PATTERN = re.compile(r"\{% endif %\}")
    FOR_PATTERN = re.compile(r"\{% for (\w+) in ([\w\.]+) %\}")
    ENDFOR_PATTERN = re.compile(r"\{% endfor %\}")

    def __init__(self, template_str: str):
        self.template_str = template_str
        self.tokens = self._parse(template_str)

    def _parse(self, text: str):
        """
        Parse template into tokens:
          ("text", content)
          ("var", varname)
          ("if", varname)
          ("endif", None)
          ("for", (varname, listname))
          ("endfor", None)
        """
        tokens = []
        pos = 0
        pattern = re.compile(
            r"(\{\{\s*[\w\.]+\s*\}\}|\{% if [\w\.]+ %\}|"
            r"\{% endif %\}|\{% for \w+ in [\w\.]+ %\}|\{% endfor %\})"
        )
        for m in pattern.finditer(text):
            if m.start() > pos:
                tokens.append(("text", text[pos:m.start()]))
            tag = m.group(0)
            if tag.startswith("{{"):
                varname = self.VAR_PATTERN.match(tag).group(1)
                tokens.append(("var", varname))
            elif tag.startswith("{% if"):
                varname = self.IF_PATTERN.match(tag).group(1)
                tokens.append(("if", varname))
            elif tag.startswith("{% endif"):
                tokens.append(("endif", None))
            elif tag.startswith("{% for"):
                loop_var, list_name = self.FOR_PATTERN.match(tag).groups()
                tokens.append(("for", (loop_var, list_name)))
            elif tag.startswith("{% endfor"):
                tokens.append(("endfor", None))
            pos = m.end()
        if pos < len(text):
            tokens.append(("text", text[pos:]))
        return tokens

    def _resolve(self, varname: str, context: dict):
        """
        Resolve a possibly-dotted varname from context dict.
        E.g. "character.name" -> context['character']['name']
        """
        parts = varname.split('.')
        val = context
        for part in parts:
            if isinstance(val, dict):
                val = val.get(part)
            else:
                val = getattr(val, part, None)
            if val is None:
                return None
        return val

    def _render_tokens(self, tokens, context: dict) -> str:
        output = []
        stack = []  # for if skip states
        skip = False
        i = 0
        while i < len(tokens):
            ttype, val = tokens[i]
            if ttype == "text":
                if not skip:
                    output.append(val)
            elif ttype == "var":
                if not skip:
                    resolved = self._resolve(val, context)
                    output.append(str(resolved) if resolved is not None else "")
            elif ttype == "if":
                resolved = self._resolve(val, context)
                cond = bool(resolved)
                stack.append(skip)
                skip = skip or not cond
            elif ttype == "endif":
                skip = stack.pop() if stack else False
            elif ttype == "for":
                loop_var, list_name = val
                # find matching endfor
                depth = 1
                inner_start = i + 1
                j = inner_start
                while j < len(tokens) and depth:
                    if tokens[j][0] == "for":
                        depth += 1
                    elif tokens[j][0] == "endfor":
                        depth -= 1
                    j += 1
                inner_tokens = tokens[inner_start:j-1]
                if not skip:
                    iterable = self._resolve(list_name, context) or []
                    for item in iterable:
                        new_ctx = context.copy()
                        new_ctx[loop_var] = item
                        output.append(self._render_tokens(inner_tokens, new_ctx))
                i = j - 1
            # endfor is a no-op here
            i += 1
        return "".join(output)

    def render(self, context: dict) -> str:
        return self._render_tokens(self.tokens, context)

    @classmethod
    def from_file(cls, filepath: str):
        with open(filepath, "r", encoding="utf-8") as f:
            return cls(f.read())
