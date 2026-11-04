# Skills and Abilities

## Ownership and data

`GameState.skill_state` stores unlocked skill IDs, each skill's level, and equipped IDs. `SkillDatabase` loads static definitions from `RPG/data/skills/`; definitions are validated at load time and are never written to saves. `SkillManager` owns progression, loadout validation, and transient monotonic cooldowns. `CombatManager` validates and applies activations, using the existing enemy, damage mitigation, reward, and combat tick paths. `StatusEffectManager` advances timed effects from the same 100 ms UI callback; it does not create its own timer.

The initial roster contains 17 skills in the physical, magical, defensive, and support categories. Power Strike and Arcane Bolt are configured starter skills. The loadout capacity is six and is set in `skill_config.json`. Unlocks and upgrades require character level and prerequisites and debit the existing Gold wallet through recorded economy transactions. Upgrade cost is the configured base multiplied by the current skill level. Skill level scales effect magnitude by 15% per level after level 1, up to the configured maximum.

## MP and regeneration

`Player.current_mp` is a separate resource; it is not a permanent stat. `maximum_mp` comes from the existing `Player.calculated_attributes.mp`, including class, race, and equipped MP bonuses. Current MP is clamped to `[0, maximum_mp]`. A successful activation consumes its configured MP once; an invalid, locked, unequipped, cooling down, or unaffordable skill consumes none. MP restoration and regeneration use the same bounds.

The existing stat calculator supplies MP regeneration:

```text
MP regeneration = (effective MP × 0.01 + effective Stamina × 0.001)
                  × class/race MP regeneration multiplier
                  + equipment MP regeneration bonus
```

The combat tick applies `MP regeneration × elapsed seconds`, with elapsed time capped at 0.25 seconds per tick. This matches the existing HP regeneration protection against stalled UI callbacks.

## Damage and effects

For each damage effect, the calculator uses this formula:

```text
skill power = (configured magnitude + Σ(effective attribute × coefficient))
              × (1 + 0.15 × (skill level - 1))
raw damage = skill power × uniform(0.95, 1.05)
critical raw damage = raw damage × existing Critical Damage (if eligible and critical)
damage reduction = selected defense / (selected defense + 1000)
final damage = max(1, raw damage × (1 - damage reduction)) for positive raw damage
```

Physical skills usually scale from effective Attack and use enemy Physical Defense. Magical skills usually scale from effective MP and use enemy Magical Defense; Update 6 does not add a separate Magical Attack stat. Both use the existing critical chance and critical damage attributes. Equipment is already included in effective attributes before skill scaling.

Damage effects support repeated hits. Healing and MP restoration use the same magnitude and level scaling, then pass through Player's bounded resource methods. Temporary buffs apply multipliers to a derived attribute view; they never modify the saved base stats. Enemy Weaken, Defense Break, and Slow use temporary enemy effects. Burn and Poison deal maximum-HP-based periodic damage, Regeneration restores player HP over time, and Stun skips an enemy action if it is active when that action is due. Poison and Burn stack up to three times; reapplying other statuses refreshes their duration. Elite, Boss, and World Boss effects have shorter durations (0.75, 0.55, and 0.4 of configured duration). Effects are transient and clear on defeat, retreat, player defeat, recovery, and encounter replacement.

Individual cooldowns use `time.monotonic()` in the application and accept explicit time values for deterministic tests. Cooldowns and active combat statuses are not saved; they reset when a CombatManager is created after load or restart.

## Adding a skill

Add a definition to the matching classification JSON file. This example requires no changes to combat code:

```json
{
  "id": "ember_lance",
  "name": "Ember Lance",
  "description": "Pierce a foe with a focused flame.",
  "classification": "magical",
  "type": "damage",
  "mp_cost": 14,
  "cooldown": 5,
  "required_level": 4,
  "unlock_gold": 120,
  "upgrade_gold": 60,
  "max_level": 5,
  "critical_eligible": true,
  "effects": [
    {"kind": "damage", "damage_type": "magical", "magnitude": 0, "scaling": {"mp": 1.6}}
  ]
}
```

Use `kind` values `damage`, `healing`, `resource_restore`, `buff`, `debuff`, or `status`. Data validation rejects malformed files, duplicate IDs, unsupported attributes and statuses, invalid costs/durations, and missing prerequisites with an error naming the file or skill. Definitions can set `rarity`, `casting_duration`, `icon`, `max_targets`, `prerequisites`, and effect `hits`, `target`, `duration`, `tick_interval`, `status`, `modifiers`, and `scaling`.

## Persistence and interface

Save schema 8 adds `character.current_mp`, `skill_state` (unlocked IDs, levels, equipped IDs, and slot capacity), and aggregate skill combat statistics. Version 7 and older saves keep their existing progression and receive full current MP and the configured starter skill state. Missing skill IDs in a save are filtered from the loadout safely. Loading does not overwrite the source save; schema 8 is written only by the normal explicit save action.

The Skills page filters the four classifications and provides unlock, upgrade, equip, and unequip actions. The Combat page shows current/max MP and six fixed hotbar slots with MP costs and cooldown countdowns. Basic attacks remain available alongside skills.

The current update does not implement skill trees, class specialization, skill evolution, casting interruption, area target selection, companions, or offline combat.
