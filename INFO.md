# Uma Musume Data Architecture

Technical notes on where different types of game data live and how community sites source them.

## Data Sources Overview

| Data Type | Source | Location |
|---|---|---|
| Character/card metadata | master.mdb | `single_mode_story_data`, `card_data`, `text_data` |
| Event names | master.mdb | `text_data` category 181 |
| Story text & dialogue | Asset bundles | `story/data/{prefix}/storytimeline_{id}` |
| Choice option text | Asset bundles | `ChoiceDataList` in `MonoBehaviour` objects |
| Choice effects (Speed +10 etc.) | **Nowhere in game files** | Crowd-sourced on wiki sites |
| Character images | Asset bundles | `chara/chr_icon_*`, `chara_stand_*` |
| Support card images | Asset bundles | `supportcard/tex_support_card_*` |
| Skill data | master.mdb | `skill_data`, `text_data` category 47 |
| Race data | master.mdb | Various `race_*` tables |

## master.mdb (SQLite)

The master database is a plain SQLite file located at `{game_root}/master.mdb` (or in the persistent data folder on device). It contains all structured game data — card stats, skill definitions, race conditions, story metadata — but **not** story text or visual assets.

### Key Tables for Events

- **`single_mode_story_data`** — Maps story IDs to cards/characters. Key columns:
  - `story_id`: Unique story identifier (e.g. `501001510`)
  - `card_id`: Non-zero for card-specific events, 0 for shared character events
  - `card_chara_id`: Character ID (e.g. 1001 = Special Week)
  - `support_card_id`: Non-zero for support card events
  - `event_category`: 1=lifecycle, 2=race/goals, 3=random events

- **`text_data`** — Localized strings keyed by `(category, index)`:
  - Category 181 = event names (index = story_id)
  - Category 170 = character names (index = chara_id)
  - Category 75 = support card names
  - Category 4 = card variant names
  - Category 47 = skill names

- **`single_mode_event_choice_reward`** — Only 57 rows. These are **display type definitions**, not per-event reward data. Maps `disp_type` to `effect_value_type` columns. This is how the game UI decides how to render the reward toast, not the actual stat gains.

- **`single_mode_story_root`** / **`single_mode_story_condition_set`** — Story branching conditions. Links stories that depend on previous choices via `condition_story_id` + `select_index`. Used for multi-part event chains, not for reward data.

### What's NOT in master.mdb

- Story dialogue text
- Choice option text
- **Actual per-event stat rewards** (Speed +10, Stamina +10, etc.)

## Asset Bundles

Game assets live in `{persistent_data}/dat/` as encrypted Unity asset bundles. A companion `meta` SQLite database indexes them.

### meta Database

The `meta` file is an **encrypted SQLite database**. It uses SQLite3MultipleCiphers with the JP key (cipher mode 3, 32-byte key). Once decrypted, the main table `a` has columns:

| Column | Meaning |
|---|---|
| `n` | Asset path (e.g. `story/data/50/5010015/storytimeline_501001510`) |
| `h` | File hash — actual filename under `dat/{h[:2]}/{h}` |
| `e` | Encryption key for XOR decryption of the bundle |

### Bundle Decryption

Bundles are XOR-encrypted with a per-bundle key derived from the meta entry's `e` column:

1. Take the 8-byte little-endian representation of entry key `e`
2. XOR each byte of the 11-byte constant `AB_KEY` with each of the 8 key bytes → 88-byte expanded key
3. XOR the first 88 bytes of the bundle with this expanded key
4. The rest of the bundle is plaintext

After decryption, bundles are standard Unity asset bundles loadable with UnityPy.

### Story Bundle Structure

Each story timeline bundle contains multiple `MonoBehaviour` objects. The ones relevant to event data are **TextClipData** objects with these fields:

```
m_Name, DataVer, Lerp, AnimationCurve, EasingType, IsEnableClip,
StartFrame, ClipLength, IsForceUpdate, _isUpdateOverBlock,
CharaId, SubCharaId, SubIconId, VoiceSheetId, CueId, UseVoiceSelector,
Name, Text, Size, IsCustomFontStyle, OutlineSizeType, GradientColorType,
OutlineColorType, NextBlock, DifferenceType, DifferenceFlag,
IsTypewriteAnimation, WaitFrame, VoiceLength, Pan3dAngle, Type, IconMode,
GainTypeOnExitLoop, ChoiceDataList, LoopCountSettingData, ColorTextInfoList,
AdditionalGradientList, FeaturesFlag, EnableClipEndSpace,
IsOverrideTypewriteSecond, OverrideTypewriteSecond,
SingleChoiceAutoSelectDuration, ShowChoiceTextToComment
```

### ChoiceDataList

Each entry in `ChoiceDataList` represents one choice option:

| Field | Type | Meaning |
|---|---|---|
| `Text` | string | Choice option text shown to the player |
| `NextBlock` | int | Which story block to jump to if selected |
| `LoopExitNextBlock` | int | Block to jump to on loop exit (-1 if N/A) |
| `DifferenceType` | int | 0 = shared, other values = gender variant |
| `DifferenceFlag` | int | 0 = shared, 2 = male trainer, other = female |
| `CharaIconId` | int | Character icon to show (0 = default) |
| `PropItemId` | int | Prop item associated with choice (0 = none) |

**There are no effect/reward fields in ChoiceDataList.** No `SuccessEffect`, no `RewardData`, no stat gain fields. The choice data only contains text and branching logic.

### Gender Variants

The game stores male and female trainer dialogue as separate entries in `ChoiceDataList`. These are **not** real player choices — they're automatically selected based on the trainer gender setting. Identifying them:

- `DifferenceFlag == 2` → male trainer variant
- Consecutive pairs with >70% text similarity (SequenceMatcher) are likely gender variants
- Gender variant pairs share the same `NextBlock` value
- Real choices have distinct `NextBlock` values per option

## Where Effects Actually Come From

**The stat rewards for event choices (Speed +10, Stamina +10, etc.) are not stored in any game data file.** They are computed at runtime by the game server/client logic and are not exposed in the master database or asset bundles.

This was confirmed by:
1. Exhaustive search of all 130+ `single_mode_*` tables — no table maps `story_id + choice_index → stat_rewards`
2. Full dump of all MonoBehaviour fields in story bundles — no effect fields exist in `ChoiceDataList` or sibling objects
3. The `single_mode_event_choice_reward` table (57 rows) only contains display type definitions, not per-event data
4. Analysis of [UmamusumeDeserializeDB5](https://github.com/UmamusumeResponseAnalyzer/UmamusumeDeserializeDB5) — the most popular open-source Uma data tool — which sources effects from an external wiki

### How Community Sites Get Effects

The chain is:

1. **kamigame.jp** (Japanese wiki) maintains a Google Sheets document with manually compiled event effects. This is crowd-sourced by players who test choices in-game and record the results.

2. The data is exposed as a JSON endpoint:
   ```
   https://kamigame.jp/vls-kamigame-gametool/json/1JrYvw5XiwWeKR5c2BKVQykutI_Lj2_zauLvaWtnzvDo_411452117.json
   ```

3. **UmamusumeDeserializeDB5** (C# tool) fetches this kamigame JSON, matches events to story IDs from master.mdb, and produces structured event data with effects.

4. Other community sites (GameTora, etc.) either scrape kamigame directly or use the output of tools like UmamusumeDeserializeDB5.

The kamigame JSON format (array of arrays):
```
[name, category, character, timing, options, successEffects, failureEffects, furigana, scenarioLink, eventName]
```

- Options and effects are `\n`-separated (one per choice)
- Effects use Japanese stat names: スピード, スタミナ, パワー, 根性, 賢さ, 体力, スキルPt
- Some effects contain `<br>` tags for grade-specific variants (G1/G2/G3/OP)

## Likely Network-Only Data

The following data is likely only available via network traffic interception (packet capture from game client ↔ server communication) and is not present in any local game files:

- **Actual stat gain values per choice** — The server calculates and sends these during gameplay. The base values on wikis are empirically determined by players.
- **Probability tables for random outcomes** — Some choices have random success/failure (e.g. "Randomly get Charming"). The actual probability weights are server-side.
- **Dynamic event conditions** — Some events trigger based on current training state, support card bonds, or scenario-specific counters. The trigger logic is in compiled game code, not data files.
- **Banner/gacha rates beyond what's legally required** — Detailed pull mechanics beyond the legally mandated disclosure.
- **Real-time multiplayer/competitive data** — Champions Meeting matchmaking, Team Stadium scoring internals.

## ID Format Reference

### Story IDs

Story IDs encode their type in the prefix:

| Prefix | Type | Example |
|---|---|---|
| `40XXXX` | Scenario events (URA, Aoharu, etc.) | `400000046` |
| `50XXXX` | Character events | `501001510` (chara 1001) |
| `80XXXX` | Support card events (R) | `800001XXX` |
| `82XXXX` | Support card events (SR) | `820001XXX` |
| `83XXXX` | Support card events (SSR) | `830001XXX` |

For character events: `50{chara_id_4d}{sequence_3d}` → `501001510` = chara 1001, story 510.

### Card IDs

Card ID format: `{chara_id}{variant}` where chara_id is 4 digits and variant is 2 digits.

- `100101` = Special Week (1001), variant 01 (base)
- `100102` = Special Week (1001), variant 02 (alt outfit)
- `103101` = Tokai Teio (1031), variant 01

### Asset Paths in meta

Story timelines: `story/data/{first2}/{first7}/storytimeline_{story_id}`
- Example: story_id `501001510` → `story/data/50/5010015/storytimeline_501001510`
