from discord import Interaction, app_commands
from discord.ext import commands
from narrative.models import CharacterTemplate, Scene, Setting
from typing import Any, Mapping, Type
from db import db

ALLOWED_FIELDS: Mapping[Type[Any], set[str]] = {
    CharacterTemplate: {"personality", "physical_description", "author_notes"},
    # Scene:             {"summary", "notes"},          # example – adjust
    # Setting:           {"value"},                     # example – adjust
}

@app_commands.command(
    name="set",
    description="Change one editable field on a record you own."
)
@app_commands.describe(
    id_or_name="ID or name of the record",
    field="Field to change (must be on the whitelist)",
    value="New value"
)
async def set_model_field(
    interaction: Interaction,
    id_or_name: str,
    field: str,
    value: str
):
    user_id = interaction.user.id

    # ------------------------------------------------------------------
    # 1. Locate the record.  (Characters first, then others)
    # ------------------------------------------------------------------
    target: Any | None = db.get_character_template_by_id_or_name(
        user_id, id_or_name
    )
    model_cls: Type[Any] | None = CharacterTemplate if target else None

    # Add more resolvers if you want to support other types via name/ID:
    if target is None:  # maybe it's a Scene ID?
        from narrative.models import Scene
        target = db.get_by_id(Scene, id_or_name)
        if target:
            model_cls = Scene

    if target is None:
        await interaction.response.send_message(
            f"❌ No record found for `{id_or_name}`.",
            ephemeral=True,
        )
        return

    # ------------------------------------------------------------------
    # 2. Verify the field is editable for this model
    # ------------------------------------------------------------------
    allowed = ALLOWED_FIELDS.get(model_cls, set())
    if field not in allowed:
        await interaction.response.send_message(
            f"❌ `{field}` cannot be changed on {model_cls.__name__}. "
            f"Allowed: {', '.join(sorted(allowed)) or 'none'}.",
            ephemeral=True,
        )
        return

    # ------------------------------------------------------------------
    # 3. Mutate & persist
    # ------------------------------------------------------------------
    setattr(target, field, value)
    db.update(target)

    await interaction.response.send_message(
        f"✅ **{field}** updated on *{getattr(target, 'name', target.id)}*.",
        ephemeral=True,
    )

async def setup(bot: commands.Bot):
  bot.tree.add_command(set_model_field, guild=None)