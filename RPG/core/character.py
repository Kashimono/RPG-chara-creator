"""Character data helpers that do not depend on the desktop UI."""

from __future__ import annotations

from .player import Player


def format_character_profile(player: Player) -> str:
    """Build the text copied by the UI for a completed character."""
    profile = player.get_character_profile()
    stats = profile["stats"]
    return (
        "========== CHARACTER PROFILE ==========\n\n"
        f"Race: {profile['race']}\n"
        f"Rarity: {profile['rarity']}\n"
        f"Level: {profile['level']}\n\n"
        "========== CHARACTER STATS ==========\n\n"
        f"HP: {stats['HP']}\n"
        f"MP: {stats['MP']}\n"
        f"Attack: {stats['Attack']}\n"
        f"Agility: {stats['Agility']}\n"
        f"Stamina: {stats['Stamina']}\n\n"
        "======================================="
    )
