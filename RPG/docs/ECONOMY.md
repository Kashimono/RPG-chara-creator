# Economy and Rewards

Update 4 adds Gold as the first currency and a small character training shop. Economy rules are independent of CustomTkinter, and the active `GameState` remains the wallet's source of truth.

## Modules and ownership

- `GameState.economy` stores currency accounts, lifetime earned/spent counters, successful purchase count, and the bounded transaction history.
- `EconomyManager` validates every credit, debit, and purchase, then updates the wallet and its transaction record together. UI code reads balances from GameState and never edits them.
- `RewardCalculator` calculates guaranteed enemy Gold from the configured enemy ID and records the factors used.
- `RewardManager` runs after the existing enemy claim guard. It calls the existing EXP award path and rolls the existing loot table once, then credits guaranteed Gold and currency loot through EconomyManager. InventoryManager collects the non-currency drops.
- `TrainingShop` validates a configured purchase and calls `Player.allocate_points`. Training uses that method's existing accepted-potential checks and does not consume level-earned stat points. Gold is committed only after the stat allocation succeeds.

## Gold rewards

`RPG/data/economy.json` contains an individual positive integer base reward for all 17 configured enemy IDs. Classification multipliers, enemy-specific multipliers, and the global multiplier default to `1.0` and must be finite and positive. If a future effect supplies a temporary multiplier, it is passed to the calculator once; no buff system is introduced here.

```text
final Gold = round-half-up(
  base Gold
  × global multiplier
  × classification multiplier
  × enemy multiplier
  × temporary multiplier
)
```

The calculator uses decimal arithmetic for the final rounding and rejects results above the supported signed 64-bit currency limit. Rewards use the enemy's immutable definition ID, so level scaling, boss phases, and previous encounter snapshots cannot multiply Gold repeatedly. The six supported classifications are Common, Uncommon, Rare, Elite, Boss, and World Boss; each enemy's base value is separately tunable.

Loot entries may add `"currency_type": "gold"`, with `min_quantity`, `max_quantity`, `drop_chance`, `rolls`, and `guaranteed` using the existing loot schema. Their quantity is a separate random Gold drop and cannot be confused with the guaranteed defeat reward. Item and currency entries with the same reward ID remain distinct. Existing loot tables without `currency_type` still load as item-like drops.

Enemy instances already provide a one-time `claim_reward()` guard, and bosses use `BossManager.claim_defeat()`. RewardManager also tracks encounter IDs for its lifetime. The same claimed defeat cannot credit Gold, award EXP, update defeat statistics, or roll loot a second time.

## Currency and transaction rules

Gold is stored as a non-negative safe integer. A successful credit updates current balance and lifetime earned; a debit updates current balance and lifetime spent. An operation that exceeds the safe range, uses an unsupported currency, has an invalid amount, or lacks funds fails before changing wallet state. Training applies its stat change before the debit commits, so rejected purchases do not alter either side.

Each successful operation records a unique transaction ID, transaction type, currency, positive amount, earned/spent direction, source, description, UTC timestamp, and optional reference ID. Rows remain in timestamp order; equal timestamps preserve operation order. The configurable history cap defaults to 100 records. Lifetime totals and purchase counts remain stored even when older history rows are pruned.

## Training shop

The initial configurable options are Strength (Attack), Vitality (HP), Agility, Endurance (Stamina), and Arcane (MP) training. Each costs 100 Gold and grants one point. Training only works after character creation and acceptance of the targeted stat's potential. Reaching potential blocks the purchase without deducting currency. The existing attribute calculation derives the updated combat attributes from the changed stat.

The Economy page shows current balance, lifetime totals, purchase count, available training, refusal reasons, and recent transactions. Dashboard displays current Gold and lifetime earned. Combat defeat feedback shows EXP, guaranteed Gold, additional Gold drops, total credited Gold, and item collection results.

Eligible inventory items can be sold through `InventoryManager`. Each sale is recorded as an earned `item_sale` transaction by `EconomyManager`. Sale value is base sell value multiplied by rarity sale multiplier and quantity, rounded to the nearest whole Gold with half values rounded upward. Inventory removal occurs only after the wallet amount and transaction are validated. Equipped items cannot be sold.

## Persistence and tuning

Save schema 7 stores economy, inventory, and equipment in the `GameState` envelope. Earlier save versions preserve their existing economy migration behavior and get empty inventory/equipment defaults. Loading does not rewrite a save; the normal explicit save operation writes schema 7.

Edit enemy rewards, multipliers, history size, or training options in `RPG/data/economy.json`. Edit currency and item drop rates and quantities in `RPG/data/loot_tables.json`. New enemy definitions need their own economy reward entry before they produce a guaranteed Gold payout. Currency support currently includes Gold only. Inventory and equipment are documented in `INVENTORY.md`.
