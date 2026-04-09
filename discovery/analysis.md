# Clairvoyance Discovery Analysis

**Total classes scanned:** 17841

**Interesting (score > 0):** 8477


## Match Reasons

| Reason | Count |
|--------|------:|
| keyword | 13965 |
| namespace | 2549 |
| signature | 1327 |

## Categories

| Category | Total | Interesting (score > 0) |
|----------|------:|------------------------:|
| skill | 613 | 397 |
| race | 3817 | 1678 |
| event | 2616 | 809 |
| training | 2242 | 937 |
| api | 1270 | 956 |
| network | 1148 | 1051 |
| master_data | 275 | 250 |
| commentary | 63 | 21 |
| other | 5797 | 2378 |

## SKILL (top 30 of 397)

### `Gallop.CardGetCardEventSkillTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.CardGetCardEventSkillResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.CardGetCardEventSkillResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.CardSkillUpgradeTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.CardSkillUpgradeResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.CardSkillUpgradeResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.SingleModeFreeGainSkillsTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.SingleModeFreeGainSkillsResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.SingleModeFreeGainSkillsResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.SingleModeGainSkillsTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.SingleModeGainSkillsResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.SingleModeGainSkillsResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.SingleModeTeamGainSkillsTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.SingleModeTeamGainSkillsResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.SingleModeTeamGainSkillsResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.SupportCardGetSupportCardEventSkillTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.SupportCardGetSupportCardEventSkillResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.SupportCardGetSupportCardEventSkillResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.MsgPack.Formatters.CardGetCardEventSkillRequestFormatter` — score 35
*methods: deserialize, serialize; MsgPack formatter*

<details><summary>Methods</summary>

- `.ctor`
- `Serialize`
- `Deserialize`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | ____keyMapping | MessagePack.Internal.AutomataDictionary |
| 24 | ____stringByteKeys | System.Byte[][] |

</details>


### `Gallop.MsgPack.Formatters.CardGetCardEventSkillResponseFormatter` — score 35
*methods: deserialize, serialize; MsgPack formatter*

<details><summary>Methods</summary>

- `.ctor`
- `Serialize`
- `Deserialize`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | ____keyMapping | MessagePack.Internal.AutomataDictionary |
| 24 | ____stringByteKeys | System.Byte[][] |

</details>


### `Gallop.MsgPack.Formatters.CardGetCardEventSkillResponse_CommonResponseFormatter` — score 35
*methods: deserialize, serialize; MsgPack formatter*

<details><summary>Methods</summary>

- `.ctor`
- `Serialize`
- `Deserialize`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | ____keyMapping | MessagePack.Internal.AutomataDictionary |
| 24 | ____stringByteKeys | System.Byte[][] |

</details>


### `Gallop.MsgPack.Formatters.CardSkillUpgradeRequestFormatter` — score 35
*methods: deserialize, serialize; MsgPack formatter*

<details><summary>Methods</summary>

- `.ctor`
- `Serialize`
- `Deserialize`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | ____keyMapping | MessagePack.Internal.AutomataDictionary |
| 24 | ____stringByteKeys | System.Byte[][] |

</details>


### `Gallop.MsgPack.Formatters.CardSkillUpgradeResponseFormatter` — score 35
*methods: deserialize, serialize; MsgPack formatter*

<details><summary>Methods</summary>

- `.ctor`
- `Serialize`
- `Deserialize`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | ____keyMapping | MessagePack.Internal.AutomataDictionary |
| 24 | ____stringByteKeys | System.Byte[][] |

</details>


### `Gallop.MsgPack.Formatters.CardSkillUpgradeResponse_CommonResponseFormatter` — score 35
*methods: deserialize, serialize; MsgPack formatter*

<details><summary>Methods</summary>

- `.ctor`
- `Serialize`
- `Deserialize`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | ____keyMapping | MessagePack.Internal.AutomataDictionary |
| 24 | ____stringByteKeys | System.Byte[][] |

</details>


### `Gallop.MsgPack.Formatters.EventSkillFormatter` — score 35
*methods: deserialize, serialize; MsgPack formatter*

<details><summary>Methods</summary>

- `.ctor`
- `Serialize`
- `Deserialize`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | ____keyMapping | MessagePack.Internal.AutomataDictionary |
| 24 | ____stringByteKeys | System.Byte[][] |

</details>


### `Gallop.MsgPack.Formatters.GainSkillInfoFormatter` — score 35
*methods: deserialize, serialize; MsgPack formatter*

<details><summary>Methods</summary>

- `.ctor`
- `Serialize`
- `Deserialize`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | ____keyMapping | MessagePack.Internal.AutomataDictionary |
| 24 | ____stringByteKeys | System.Byte[][] |

</details>


### `Gallop.MsgPack.Formatters.SingleModeFreeGainSkillsRequestFormatter` — score 35
*methods: deserialize, serialize; MsgPack formatter*

<details><summary>Methods</summary>

- `.ctor`
- `Serialize`
- `Deserialize`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | ____keyMapping | MessagePack.Internal.AutomataDictionary |
| 24 | ____stringByteKeys | System.Byte[][] |

</details>


### `Gallop.MsgPack.Formatters.SingleModeFreeGainSkillsResponseFormatter` — score 35
*methods: deserialize, serialize; MsgPack formatter*

<details><summary>Methods</summary>

- `.ctor`
- `Serialize`
- `Deserialize`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | ____keyMapping | MessagePack.Internal.AutomataDictionary |
| 24 | ____stringByteKeys | System.Byte[][] |

</details>


### `Gallop.MsgPack.Formatters.SingleModeFreeGainSkillsResponse_CommonResponseFormatter` — score 35
*methods: deserialize, serialize; MsgPack formatter*

<details><summary>Methods</summary>

- `.ctor`
- `Serialize`
- `Deserialize`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | ____keyMapping | MessagePack.Internal.AutomataDictionary |
| 24 | ____stringByteKeys | System.Byte[][] |

</details>


### `Gallop.MsgPack.Formatters.SingleModeGainSkillsRequestFormatter` — score 35
*methods: deserialize, serialize; MsgPack formatter*

<details><summary>Methods</summary>

- `.ctor`
- `Serialize`
- `Deserialize`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | ____keyMapping | MessagePack.Internal.AutomataDictionary |
| 24 | ____stringByteKeys | System.Byte[][] |

</details>


### `Gallop.MsgPack.Formatters.SingleModeGainSkillsResponseFormatter` — score 35
*methods: deserialize, serialize; MsgPack formatter*

<details><summary>Methods</summary>

- `.ctor`
- `Serialize`
- `Deserialize`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | ____keyMapping | MessagePack.Internal.AutomataDictionary |
| 24 | ____stringByteKeys | System.Byte[][] |

</details>


### `Gallop.MsgPack.Formatters.SingleModeGainSkillsResponse_CommonResponseFormatter` — score 35
*methods: deserialize, serialize; MsgPack formatter*

<details><summary>Methods</summary>

- `.ctor`
- `Serialize`
- `Deserialize`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | ____keyMapping | MessagePack.Internal.AutomataDictionary |
| 24 | ____stringByteKeys | System.Byte[][] |

</details>


### `Gallop.MsgPack.Formatters.SingleModeTeamGainSkillsRequestFormatter` — score 35
*methods: deserialize, serialize; MsgPack formatter*

<details><summary>Methods</summary>

- `.ctor`
- `Serialize`
- `Deserialize`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | ____keyMapping | MessagePack.Internal.AutomataDictionary |
| 24 | ____stringByteKeys | System.Byte[][] |

</details>


### `Gallop.MsgPack.Formatters.SingleModeTeamGainSkillsResponseFormatter` — score 35
*methods: deserialize, serialize; MsgPack formatter*

<details><summary>Methods</summary>

- `.ctor`
- `Serialize`
- `Deserialize`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | ____keyMapping | MessagePack.Internal.AutomataDictionary |
| 24 | ____stringByteKeys | System.Byte[][] |

</details>


### `Gallop.MsgPack.Formatters.SingleModeTeamGainSkillsResponse_CommonResponseFormatter` — score 35
*methods: deserialize, serialize; MsgPack formatter*

<details><summary>Methods</summary>

- `.ctor`
- `Serialize`
- `Deserialize`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | ____keyMapping | MessagePack.Internal.AutomataDictionary |
| 24 | ____stringByteKeys | System.Byte[][] |

</details>


### `Gallop.MsgPack.Formatters.SkillDataFormatter` — score 35
*methods: deserialize, serialize; MsgPack formatter*

<details><summary>Methods</summary>

- `.ctor`
- `Serialize`
- `Deserialize`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | ____keyMapping | MessagePack.Internal.AutomataDictionary |
| 24 | ____stringByteKeys | System.Byte[][] |

</details>


### `Gallop.MsgPack.Formatters.SkillTipsFormatter` — score 35
*methods: deserialize, serialize; MsgPack formatter*

<details><summary>Methods</summary>

- `.ctor`
- `Serialize`
- `Deserialize`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | ____keyMapping | MessagePack.Internal.AutomataDictionary |
| 24 | ____stringByteKeys | System.Byte[][] |

</details>


### `Gallop.MsgPack.Formatters.StoryDirectSkillSetFormatter` — score 35
*methods: deserialize, serialize; MsgPack formatter*

<details><summary>Methods</summary>

- `.ctor`
- `Serialize`
- `Deserialize`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | ____keyMapping | MessagePack.Internal.AutomataDictionary |
| 24 | ____stringByteKeys | System.Byte[][] |

</details>


### `Gallop.MsgPack.Formatters.SupportCardGetSupportCardEventSkillRequestFormatter` — score 35
*methods: deserialize, serialize; MsgPack formatter*

<details><summary>Methods</summary>

- `.ctor`
- `Serialize`
- `Deserialize`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | ____keyMapping | MessagePack.Internal.AutomataDictionary |
| 24 | ____stringByteKeys | System.Byte[][] |

</details>


### `Gallop.MsgPack.Formatters.SupportCardGetSupportCardEventSkillResponseFormatter` — score 35
*methods: deserialize, serialize; MsgPack formatter*

<details><summary>Methods</summary>

- `.ctor`
- `Serialize`
- `Deserialize`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | ____keyMapping | MessagePack.Internal.AutomataDictionary |
| 24 | ____stringByteKeys | System.Byte[][] |

</details>


### `Gallop.MsgPack.Formatters.SupportCardGetSupportCardEventSkillResponse_CommonResponseFormatter` — score 35
*methods: deserialize, serialize; MsgPack formatter*

<details><summary>Methods</summary>

- `.ctor`
- `Serialize`
- `Deserialize`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | ____keyMapping | MessagePack.Internal.AutomataDictionary |
| 24 | ____stringByteKeys | System.Byte[][] |

</details>


### `Gallop.MsgPack.Formatters.TeamSkillTipsFormatter` — score 35
*methods: deserialize, serialize; MsgPack formatter*

<details><summary>Methods</summary>

- `.ctor`
- `Serialize`
- `Deserialize`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | ____keyMapping | MessagePack.Internal.AutomataDictionary |
| 24 | ____stringByteKeys | System.Byte[][] |

</details>


## RACE (top 30 of 1678)

### `Gallop.RaceHorseSimulateData` — score 63
*methods: deserialize; fields: cardid, charaid, guts, speed, stamina, viewerid*

<details><summary>Methods</summary>

- `Deserialize`
- `ToRaceHorseData`
- `.ctor`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | ViewerId | System.Int64 |
| 24 | SingleModeCharaId | System.Int32 |
| 28 | CardId | System.Int32 |
| 32 | CharaId | System.Int32 |
| 36 | RunningStyle | System.Int32 |
| 40 | SkillNum | System.Int32 |
| 48 | SkillDataArray | Gallop.SkillData[] |
| 56 | Speed | System.Int32 |
| 60 | Stamina | System.Int32 |
| 64 | Pow | System.Int32 |
| 68 | Guts | System.Int32 |
| 72 | Wiz | System.Int32 |
| 76 | FinalGrade | System.Int32 |
| 80 | Popularity | System.Int32 |
| 88 | PopularityMarkRankArray | System.Int32[] |
| 96 | ProperDistanceShort | System.Int32 |
| 100 | ProperDistanceMile | System.Int32 |
| 104 | ProperDistanceMiddle | System.Int32 |
| 108 | ProperDistanceLong | System.Int32 |
| 112 | ProperRunningStyleNige | System.Int32 |
| 116 | ProperRunningStyleSenko | System.Int32 |
| 120 | ProperRunningStyleSashi | System.Int32 |
| 124 | ProperRunningStyleOikomi | System.Int32 |
| 128 | ProperGroundTurf | System.Int32 |
| 132 | ProperGroundDirt | System.Int32 |
| 136 | Motivation | System.Int32 |
| 140 | FrameOrder | System.Int32 |
| 144 | TeamId | System.Int32 |
| 148 | TeamMemberId | System.Int32 |
| 152 | ItemNum | System.Int32 |
| 160 | ItemIdArray | System.Int32[] |
| 168 | TeamRank | System.Int32 |
| 172 | SingleModeWinCount | System.Int32 |

</details>


### `Gallop.RaceSimulateRequest` — score 46
*methods: deserialize; fields: season, weather; API pattern*

<details><summary>Methods</summary>

- `Deserialize`
- `.ctor`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | ResourceVer | System.String |
| 24 | RaceInstanceId | System.Int32 |
| 28 | RandomSeed | System.Int32 |
| 32 | Season | System.Int32 |
| 36 | Weather | System.Int32 |
| 40 | GroundCondition | System.Int32 |
| 44 | RaceHorseNum | System.Int32 |
| 48 | RaceHorseDataArray | Gallop.RaceHorseSimulateData[] |
| 56 | RaceType | System.Int32 |
| 60 | SelfEvaluate | System.Int32 |
| 64 | OpponentEvaluate | System.Int32 |
| 68 | ScoreCalcTeamId | System.Int32 |
| 72 | SupportCardScoreBonus | System.Int32 |
| 76 | ChallengeMatchDifficulty | System.Int32 |
| 80 | Reserve0 | System.Int32 |

</details>


### `Gallop.MasterTeamBuildingRaceNpc.TeamBuildingRaceNpc` — score 45
*fields: charaid, guts, speed, stamina; Master data*

<details><summary>Methods</summary>

- `.ctor`
- `get_IsMobCharaData`
- `GetName`
- `GetProperGround`
- `GetProperDistance`
- `GetProperRunningStyle`
- `GetMaxProperGroundType`
- `GetMaxProperDistanceType`
- `GetMaxProperRunningStyle`
- `GetHaveSkillCount`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | Id | System.Int32 |
| 20 | NpcGroupId | System.Int32 |
| 24 | CharaId | System.Int32 |
| 28 | MobId | System.Int32 |
| 32 | RaceDressId | System.Int32 |
| 36 | Speed | System.Int32 |
| 40 | Stamina | System.Int32 |
| 44 | Pow | System.Int32 |
| 48 | Guts | System.Int32 |
| 52 | Wiz | System.Int32 |
| 56 | ProperDistanceShort | System.Int32 |
| 60 | ProperDistanceMile | System.Int32 |
| 64 | ProperDistanceMiddle | System.Int32 |
| 68 | ProperDistanceLong | System.Int32 |
| 72 | ProperRunningStyleNige | System.Int32 |
| 76 | ProperRunningStyleSenko | System.Int32 |
| 80 | ProperRunningStyleSashi | System.Int32 |
| 84 | ProperRunningStyleOikomi | System.Int32 |
| 88 | ProperGroundTurf | System.Int32 |
| 92 | ProperGroundDirt | System.Int32 |
| 96 | SkillSetId | System.Int32 |
| 0 | INVALID_MOB_ID | System.Int32 |

</details>


### `Gallop.RaceSimulateHorseFrameData` — score 41
*methods: deserialize, serialize; fields: distance, speed*

<details><summary>Methods</summary>

- `.ctor`
- `Record`
- `CalcSize`
- `Serialize`
- `Deserialize`
- `Deserialize_Ver20201027_OrNewer`
- `Deserialize_Ver20200406_OrNewer`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 0 | BLOCK_HORSEINDEX_NULL | System.Int32 |
| 16 | Distance | System.Single |
| 20 | LanePosition | System.Single |
| 24 | Speed | System.Single |
| 28 | Hp | System.Single |
| 32 | TemptationMode | System.SByte |
| 33 | BlockFrontHorseIndex | System.SByte |
| 0 | SpeedAccuracy | System.Single |
| 0 | LaneAccuracy | System.Single |

</details>


### `Gallop.MasterChallengeMatchRaceNpc.ChallengeMatchRaceNpc` — score 40
*fields: charaid, guts, speed, stamina; Master data*

<details><summary>Methods</summary>

- `.ctor`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | Id | System.Int32 |
| 20 | NpcGroupId | System.Int32 |
| 24 | CharaId | System.Int32 |
| 28 | MobId | System.Int32 |
| 32 | RaceDressId | System.Int32 |
| 36 | RaceInstanceId | System.Int32 |
| 40 | Speed | System.Int32 |
| 44 | Stamina | System.Int32 |
| 48 | Pow | System.Int32 |
| 52 | Guts | System.Int32 |
| 56 | Wiz | System.Int32 |
| 60 | ProperDistanceShort | System.Int32 |
| 64 | ProperDistanceMile | System.Int32 |
| 68 | ProperDistanceMiddle | System.Int32 |
| 72 | ProperDistanceLong | System.Int32 |
| 76 | ProperRunningStyleNige | System.Int32 |
| 80 | ProperRunningStyleSenko | System.Int32 |
| 84 | ProperRunningStyleSashi | System.Int32 |
| 88 | ProperRunningStyleOikomi | System.Int32 |
| 92 | ProperGroundTurf | System.Int32 |
| 96 | ProperGroundDirt | System.Int32 |
| 100 | SkillSetId | System.Int32 |

</details>


### `Gallop.MasterDailyRaceNpc.DailyRaceNpc` — score 40
*fields: charaid, guts, speed, stamina; Master data*

<details><summary>Methods</summary>

- `.ctor`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | Id | System.Int32 |
| 20 | NpcGroupId | System.Int32 |
| 24 | CharaId | System.Int32 |
| 28 | MobId | System.Int32 |
| 32 | RaceDressId | System.Int32 |
| 36 | RaceInstanceId | System.Int32 |
| 40 | Speed | System.Int32 |
| 44 | Stamina | System.Int32 |
| 48 | Pow | System.Int32 |
| 52 | Guts | System.Int32 |
| 56 | Wiz | System.Int32 |
| 60 | ProperDistanceShort | System.Int32 |
| 64 | ProperDistanceMile | System.Int32 |
| 68 | ProperDistanceMiddle | System.Int32 |
| 72 | ProperDistanceLong | System.Int32 |
| 76 | ProperRunningStyleNige | System.Int32 |
| 80 | ProperRunningStyleSenko | System.Int32 |
| 84 | ProperRunningStyleSashi | System.Int32 |
| 88 | ProperRunningStyleOikomi | System.Int32 |
| 92 | ProperGroundTurf | System.Int32 |
| 96 | ProperGroundDirt | System.Int32 |
| 100 | SkillSetId | System.Int32 |

</details>


### `Gallop.MasterLegendRaceBossNpc.LegendRaceBossNpc` — score 40
*fields: charaid, guts, speed, stamina; Master data*

<details><summary>Methods</summary>

- `.ctor`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | Id | System.Int32 |
| 20 | CharaId | System.Int32 |
| 24 | RaceDressId | System.Int32 |
| 28 | NicknameId | System.Int32 |
| 32 | CardRarityDataId | System.Int32 |
| 36 | Post | System.Int32 |
| 40 | Speed | System.Int32 |
| 44 | Stamina | System.Int32 |
| 48 | Pow | System.Int32 |
| 52 | Guts | System.Int32 |
| 56 | Wiz | System.Int32 |
| 60 | ProperDistanceShort | System.Int32 |
| 64 | ProperDistanceMile | System.Int32 |
| 68 | ProperDistanceMiddle | System.Int32 |
| 72 | ProperDistanceLong | System.Int32 |
| 76 | ProperRunningStyleNige | System.Int32 |
| 80 | ProperRunningStyleSenko | System.Int32 |
| 84 | ProperRunningStyleSashi | System.Int32 |
| 88 | ProperRunningStyleOikomi | System.Int32 |
| 92 | ProperGroundTurf | System.Int32 |
| 96 | ProperGroundDirt | System.Int32 |
| 100 | SkillSetId | System.Int32 |

</details>


### `Gallop.MasterLegendRaceNpc.LegendRaceNpc` — score 40
*fields: charaid, guts, speed, stamina; Master data*

<details><summary>Methods</summary>

- `.ctor`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | Id | System.Int32 |
| 20 | NpcGroupId | System.Int32 |
| 24 | CharaId | System.Int32 |
| 28 | MobId | System.Int32 |
| 32 | RaceDressId | System.Int32 |
| 36 | RaceInstanceId | System.Int32 |
| 40 | Speed | System.Int32 |
| 44 | Stamina | System.Int32 |
| 48 | Pow | System.Int32 |
| 52 | Guts | System.Int32 |
| 56 | Wiz | System.Int32 |
| 60 | ProperDistanceShort | System.Int32 |
| 64 | ProperDistanceMile | System.Int32 |
| 68 | ProperDistanceMiddle | System.Int32 |
| 72 | ProperDistanceLong | System.Int32 |
| 76 | ProperRunningStyleNige | System.Int32 |
| 80 | ProperRunningStyleSenko | System.Int32 |
| 84 | ProperRunningStyleSashi | System.Int32 |
| 88 | ProperRunningStyleOikomi | System.Int32 |
| 92 | ProperGroundTurf | System.Int32 |
| 96 | ProperGroundDirt | System.Int32 |
| 100 | SkillSetId | System.Int32 |

</details>


### `Gallop.MasterMainStoryRaceCharaData.MainStoryRaceCharaData` — score 40
*fields: charaid, guts, speed, stamina; Master data*

<details><summary>Methods</summary>

- `.ctor`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | Id | System.Int32 |
| 20 | GroupId | System.Int32 |
| 24 | BracketNumber | System.Int32 |
| 28 | CharaId | System.Int32 |
| 32 | MobId | System.Int32 |
| 36 | IsPlayer | System.Int32 |
| 40 | DressId | System.Int32 |
| 44 | CharaColorType | System.Int32 |
| 48 | Motivation | System.Int32 |
| 52 | RunningStyle | System.Int32 |
| 56 | Speed | System.Int32 |
| 60 | Stamina | System.Int32 |
| 64 | Pow | System.Int32 |
| 68 | Guts | System.Int32 |
| 72 | Wiz | System.Int32 |
| 76 | ProperDistanceShort | System.Int32 |
| 80 | ProperDistanceMile | System.Int32 |
| 84 | ProperDistanceMiddle | System.Int32 |
| 88 | ProperDistanceLong | System.Int32 |
| 92 | ProperRunningStyleNige | System.Int32 |
| 96 | ProperRunningStyleSenko | System.Int32 |
| 100 | ProperRunningStyleSashi | System.Int32 |
| 104 | ProperRunningStyleOikomi | System.Int32 |
| 108 | ProperGroundTurf | System.Int32 |
| 112 | ProperGroundDirt | System.Int32 |
| 116 | SkillSetId | System.Int32 |
| 120 | ShowSkillType | System.Int32 |

</details>


### `Gallop.ChallengeMatchRaceEndTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.ChallengeMatchRaceEndResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.ChallengeMatchRaceEndResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.ChallengeMatchRaceEntryTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.ChallengeMatchRaceEntryResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.ChallengeMatchRaceEntryResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.ChallengeMatchRaceOpenTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.ChallengeMatchRaceOpenResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.ChallengeMatchRaceOpenResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.ChallengeMatchRaceStartTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.ChallengeMatchRaceStartResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.ChallengeMatchRaceStartResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.ChampionsFinalRaceEndTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.ChampionsFinalRaceEndResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.ChampionsFinalRaceEndResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.ChampionsFinalRaceRankingTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.ChampionsFinalRaceRankingResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.ChampionsFinalRaceRankingResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.ChampionsFinalRaceStartTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.ChampionsFinalRaceStartResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.ChampionsFinalRaceStartResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.ChampionsRaceEndTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.ChampionsRaceEndResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.ChampionsRaceEndResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.ChampionsRaceEntryTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.ChampionsRaceEntryResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.ChampionsRaceEntryResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.ChampionsRaceStartTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.ChampionsRaceStartResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.ChampionsRaceStartResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.DailyLegendRaceGetRewardListTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.DailyLegendRaceGetRewardListResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.DailyLegendRaceGetRewardListResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.DailyLegendRaceIndexTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.DailyLegendRaceIndexResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.DailyLegendRaceIndexResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.DailyLegendRaceRaceEntryTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.DailyLegendRaceRaceEntryResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.DailyLegendRaceRaceEntryResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.DailyLegendRaceRaceStartTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.DailyLegendRaceRaceStartResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.DailyLegendRaceRaceStartResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.DailyLegendRaceReflectItemEffectTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.DailyLegendRaceReflectItemEffectResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.DailyLegendRaceReflectItemEffectResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.DailyLegendRaceReplayCheckTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.DailyLegendRaceReplayCheckResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.DailyLegendRaceReplayCheckResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.DailyLegendRaceResetTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.DailyLegendRaceResetResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.DailyLegendRaceResetResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.DailyLegendRaceResumeTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.DailyLegendRaceResumeResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.DailyLegendRaceResumeResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.DailyRaceGetRewardListTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.DailyRaceGetRewardListResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.DailyRaceGetRewardListResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.DailyRaceIndexTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.DailyRaceIndexResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.DailyRaceIndexResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.DailyRacePreReplayCheckTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.DailyRacePreReplayCheckResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.DailyRacePreReplayCheckResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


## EVENT (top 30 of 809)

### `Gallop.ChampionsGetRaceHistoryInfoTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.ChampionsGetRaceHistoryInfoResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.ChampionsGetRaceHistoryInfoResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.CharacterStoryFirstClearTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.CharacterStoryFirstClearResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.CharacterStoryFirstClearResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.DebugSingleModeStoryDirectTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.DebugSingleModeStoryDirectResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.DebugSingleModeStoryDirectResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.ExtraStoryFirstClearTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.ExtraStoryFirstClearResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.ExtraStoryFirstClearResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.GachaGetHistoryTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.GachaGetHistoryResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.GachaGetHistoryResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.GachaGetPrizeHistoryTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.GachaGetPrizeHistoryResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.GachaGetPrizeHistoryResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.GalleryPlayEventTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.GalleryPlayEventResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.GalleryPlayEventResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.JukeboxHistoryTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.JukeboxHistoryResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.JukeboxHistoryResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.MainStoryFirstClearTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.MainStoryFirstClearResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.MainStoryFirstClearResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.MainStoryRaceGetRaceTableTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.MainStoryRaceGetRaceTableResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.MainStoryRaceGetRaceTableResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.PresentHistoryTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.PresentHistoryResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.PresentHistoryResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.SingleModeCheckEventTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.SingleModeCheckEventResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.SingleModeCheckEventResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.SingleModeFreeCheckEventTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.SingleModeFreeCheckEventResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.SingleModeFreeCheckEventResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.SingleModeFreeChoiceRewardTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.SingleModeFreeChoiceRewardResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.SingleModeFreeChoiceRewardResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.SingleModeGetChoiceRewardTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.SingleModeGetChoiceRewardResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.SingleModeGetChoiceRewardResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.SingleModeTeamCheckEventTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.SingleModeTeamCheckEventResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.SingleModeTeamCheckEventResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.SingleModeTeamGetChoiceRewardTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.SingleModeTeamGetChoiceRewardResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.SingleModeTeamGetChoiceRewardResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.StoryEventAnnounceTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.StoryEventAnnounceResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.StoryEventAnnounceResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.StoryEventIndexTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.StoryEventIndexResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.StoryEventIndexResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.StoryEventReceiveMissionTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.StoryEventReceiveMissionResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.StoryEventReceiveMissionResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.StoryEventRouletteTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.StoryEventRouletteResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.StoryEventRouletteResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.StoryEventRouletteChangeSheetTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.StoryEventRouletteChangeSheetResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.StoryEventRouletteChangeSheetResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.StoryEventRouletteExecTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.StoryEventRouletteExecResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.StoryEventRouletteExecResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.StoryEventStoryClearTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.StoryEventStoryClearResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.StoryEventStoryClearResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.UserChangeStoryFavoriteTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.UserChangeStoryFavoriteResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.UserChangeStoryFavoriteResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.MsgPack.Formatters.ChampionsGetRaceHistoryInfoRequestFormatter` — score 35
*methods: deserialize, serialize; MsgPack formatter*

<details><summary>Methods</summary>

- `.ctor`
- `Serialize`
- `Deserialize`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | ____keyMapping | MessagePack.Internal.AutomataDictionary |
| 24 | ____stringByteKeys | System.Byte[][] |

</details>


### `Gallop.MsgPack.Formatters.ChampionsGetRaceHistoryInfoResponseFormatter` — score 35
*methods: deserialize, serialize; MsgPack formatter*

<details><summary>Methods</summary>

- `.ctor`
- `Serialize`
- `Deserialize`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | ____keyMapping | MessagePack.Internal.AutomataDictionary |
| 24 | ____stringByteKeys | System.Byte[][] |

</details>


### `Gallop.MsgPack.Formatters.ChampionsGetRaceHistoryInfoResponse_CommonResponseFormatter` — score 35
*methods: deserialize, serialize; MsgPack formatter*

<details><summary>Methods</summary>

- `.ctor`
- `Serialize`
- `Deserialize`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | ____keyMapping | MessagePack.Internal.AutomataDictionary |
| 24 | ____stringByteKeys | System.Byte[][] |

</details>


### `Gallop.MsgPack.Formatters.CharacterStoryDataFormatter` — score 35
*methods: deserialize, serialize; MsgPack formatter*

<details><summary>Methods</summary>

- `.ctor`
- `Serialize`
- `Deserialize`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | ____keyMapping | MessagePack.Internal.AutomataDictionary |
| 24 | ____stringByteKeys | System.Byte[][] |

</details>


### `Gallop.MsgPack.Formatters.CharacterStoryFirstClearRequestFormatter` — score 35
*methods: deserialize, serialize; MsgPack formatter*

<details><summary>Methods</summary>

- `.ctor`
- `Serialize`
- `Deserialize`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | ____keyMapping | MessagePack.Internal.AutomataDictionary |
| 24 | ____stringByteKeys | System.Byte[][] |

</details>


## TRAINING (top 30 of 937)

### `Gallop.MasterSingleModeNpc.SingleModeNpc` — score 40
*fields: charaid, guts, speed, stamina; Master data*

<details><summary>Methods</summary>

- `.ctor`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | Id | System.Int32 |
| 20 | NpcGroupId | System.Int32 |
| 24 | CharaId | System.Int32 |
| 28 | MobId | System.Int32 |
| 32 | RaceDressId | System.Int32 |
| 36 | Speed | System.Int32 |
| 40 | Stamina | System.Int32 |
| 44 | Pow | System.Int32 |
| 48 | Guts | System.Int32 |
| 52 | Wiz | System.Int32 |
| 56 | ProperDistanceShort | System.Int32 |
| 60 | ProperDistanceMile | System.Int32 |
| 64 | ProperDistanceMiddle | System.Int32 |
| 68 | ProperDistanceLong | System.Int32 |
| 72 | ProperRunningStyleNige | System.Int32 |
| 76 | ProperRunningStyleSenko | System.Int32 |
| 80 | ProperRunningStyleSashi | System.Int32 |
| 84 | ProperRunningStyleOikomi | System.Int32 |
| 88 | ProperGroundTurf | System.Int32 |
| 92 | ProperGroundDirt | System.Int32 |
| 96 | SkillSetId | System.Int32 |
| 100 | MotivationMin | System.Int32 |
| 104 | MotivationMax | System.Int32 |

</details>


### `Gallop.MasterSingleModeScoutChara.SingleModeScoutChara` — score 40
*fields: charaid, guts, speed, stamina; Master data*

<details><summary>Methods</summary>

- `.ctor`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | Id | System.Int32 |
| 20 | SupportCardId | System.Int32 |
| 24 | CharaId | System.Int32 |
| 28 | RaceDressId | System.Int32 |
| 32 | LiveDressId | System.Int32 |
| 36 | TagSupportCardId | System.Int32 |
| 40 | Speed | System.Int32 |
| 44 | Stamina | System.Int32 |
| 48 | Pow | System.Int32 |
| 52 | Guts | System.Int32 |
| 56 | Wiz | System.Int32 |
| 60 | ProperDistanceShort | System.Int32 |
| 64 | ProperDistanceMile | System.Int32 |
| 68 | ProperDistanceMiddle | System.Int32 |
| 72 | ProperDistanceLong | System.Int32 |
| 76 | ProperRunningStyleNige | System.Int32 |
| 80 | ProperRunningStyleSenko | System.Int32 |
| 84 | ProperRunningStyleSashi | System.Int32 |
| 88 | ProperRunningStyleOikomi | System.Int32 |
| 92 | ProperGroundTurf | System.Int32 |
| 96 | ProperGroundDirt | System.Int32 |
| 100 | SpeedLimit | System.Int32 |
| 104 | StaminaLimit | System.Int32 |
| 108 | PowLimit | System.Int32 |
| 112 | GutsLimit | System.Int32 |
| 116 | WizLimit | System.Int32 |

</details>


### `Gallop.PreSingleModeFriendSupportCardReloadTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.PreSingleModeFriendSupportCardReloadResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.PreSingleModeFriendSupportCardReloadResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.PreSingleModeIndexTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.PreSingleModeIndexResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.PreSingleModeIndexResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.SingleModeChangeRunningStyleTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.SingleModeChangeRunningStyleResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.SingleModeChangeRunningStyleResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.SingleModeChangeShortCutTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.SingleModeChangeShortCutResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.SingleModeChangeShortCutResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.SingleModeContinueTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.SingleModeContinueResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.SingleModeContinueResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.SingleModeExecCommandTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.SingleModeExecCommandResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.SingleModeExecCommandResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.SingleModeFinishTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.SingleModeFinishResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.SingleModeFinishResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.SingleModeFreeChangeRunningStyleTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.SingleModeFreeChangeRunningStyleResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.SingleModeFreeChangeRunningStyleResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.SingleModeFreeChangeShortCutTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.SingleModeFreeChangeShortCutResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.SingleModeFreeChangeShortCutResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.SingleModeFreeContinueTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.SingleModeFreeContinueResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.SingleModeFreeContinueResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.SingleModeFreeExecCommandTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.SingleModeFreeExecCommandResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.SingleModeFreeExecCommandResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.SingleModeFreeFinishTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.SingleModeFreeFinishResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.SingleModeFreeFinishResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.SingleModeFreeLoadTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.SingleModeFreeLoadResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.SingleModeFreeLoadResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.SingleModeFreeMinigameEndTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.SingleModeFreeMinigameEndResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.SingleModeFreeMinigameEndResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.SingleModeFreeMultiItemExchangeTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.SingleModeFreeMultiItemExchangeResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.SingleModeFreeMultiItemExchangeResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.SingleModeFreeMultiItemExchange2Task` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.SingleModeFreeMultiItemExchange2Response> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.SingleModeFreeMultiItemExchange2Response> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.SingleModeFreeMultiItemUseTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.SingleModeFreeMultiItemUseResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.SingleModeFreeMultiItemUseResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.SingleModeFreeStartTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.SingleModeFreeStartResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.SingleModeFreeStartResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.SingleModeLoadTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.SingleModeLoadResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.SingleModeLoadResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.SingleModeMinigameEndTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.SingleModeMinigameEndResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.SingleModeMinigameEndResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.SingleModeStartTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.SingleModeStartResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.SingleModeStartResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.SingleModeTeamChangeRunningStyleTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.SingleModeTeamChangeRunningStyleResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.SingleModeTeamChangeRunningStyleResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.SingleModeTeamChangeShortCutTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.SingleModeTeamChangeShortCutResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.SingleModeTeamChangeShortCutResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.SingleModeTeamContinueTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.SingleModeTeamContinueResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.SingleModeTeamContinueResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.SingleModeTeamExecCommandTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.SingleModeTeamExecCommandResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.SingleModeTeamExecCommandResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.SingleModeTeamFinishTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.SingleModeTeamFinishResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.SingleModeTeamFinishResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.SingleModeTeamLoadTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.SingleModeTeamLoadResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.SingleModeTeamLoadResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.SingleModeTeamMinigameEndTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.SingleModeTeamMinigameEndResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.SingleModeTeamMinigameEndResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


## API (top 30 of 956)

### `Gallop.AccountChainDisconnectTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.AccountChainDisconnectResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.AccountChainDisconnectResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.AccountDeletionCancelTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.AccountDeletionCancelResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.AccountDeletionCancelResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.AccountDeletionRequestTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.AccountDeletionRequestResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.AccountDeletionRequestResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.AccountSteamChainDisconnectTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.AccountSteamChainDisconnectResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.AccountSteamChainDisconnectResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.BannerUrlTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.BannerUrlResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.BannerUrlResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.CabinedAccountGetMailInfoTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.CabinedAccountGetMailInfoResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.CabinedAccountGetMailInfoResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.CabinedAccountRegisterEmailAddressTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.CabinedAccountRegisterEmailAddressResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.CabinedAccountRegisterEmailAddressResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.CabinedAccountSendAuthCodeTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.CabinedAccountSendAuthCodeResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.CabinedAccountSendAuthCodeResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.CabinedAccountSendVerificationUrlTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.CabinedAccountSendVerificationUrlResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.CabinedAccountSendVerificationUrlResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.CardGetReleaseCardTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.CardGetReleaseCardResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.CardGetReleaseCardResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.CardRarityUpgradeTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.CardRarityUpgradeResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.CardRarityUpgradeResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.CardSellPieceTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.CardSellPieceResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.CardSellPieceResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.CardTalentStrengthenTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.CardTalentStrengthenResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.CardTalentStrengthenResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.CardUnlockTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.CardUnlockResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.CardUnlockResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.ChallengeMatchIndexTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.ChallengeMatchIndexResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.ChallengeMatchIndexResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.ChallengeMatchReflectItemEffectTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.ChallengeMatchReflectItemEffectResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.ChallengeMatchReflectItemEffectResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.ChallengeMatchResetTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.ChallengeMatchResetResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.ChallengeMatchResetResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.ChallengeMatchResumeTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.ChallengeMatchResumeResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.ChallengeMatchResumeResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.ChampionsCancelTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.ChampionsCancelResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.ChampionsCancelResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.ChampionsEntryTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.ChampionsEntryResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.ChampionsEntryResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.ChampionsFinalRoundEndTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.ChampionsFinalRoundEndResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.ChampionsFinalRoundEndResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.ChampionsGetNewsInfoTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.ChampionsGetNewsInfoResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.ChampionsGetNewsInfoResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.ChampionsGetNewsWinInfoTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.ChampionsGetNewsWinInfoResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.ChampionsGetNewsWinInfoResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.ChampionsGetRaceResultChartTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.ChampionsGetRaceResultChartResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.ChampionsGetRaceResultChartResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.ChampionsGetRankingCharaInfoTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.ChampionsGetRankingCharaInfoResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.ChampionsGetRankingCharaInfoResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.ChampionsGetRewardArrayTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.ChampionsGetRewardArrayResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.ChampionsGetRewardArrayResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.ChampionsIndexTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.ChampionsIndexResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.ChampionsIndexResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.ChampionsLobbyTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.ChampionsLobbyResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.ChampionsLobbyResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.ChampionsPaddockIndexTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.ChampionsPaddockIndexResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.ChampionsPaddockIndexResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


### `Gallop.ChampionsPollTask` — score 40
*methods: deserialize, onerror; API pattern*

<details><summary>Methods</summary>

- `get_CacheTime`
- `get_IsCompressed`
- `.ctor`
- `SetHeader`
- `Send`
- `Deserialize`
- `OnError`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | postData | System.Byte[] |
| 24 | onSuccess | System.Action<Gallop.ChampionsPollResponse> |
| 32 | onError | System.Action<Cute.Http.ErrorType,System.Int32,Gallop.ChampionsPollResponse> |
| 40 | headers | System.Collections.Generic.Dictionary<System.String,System.String> |
| 48 | request | Cute.Http.IWebRequest |

</details>


## NETWORK (top 30 of 1051)

### `Gallop.MsgPack.Formatters.AccountChainDisconnectRequestFormatter` — score 35
*methods: deserialize, serialize; MsgPack formatter*

<details><summary>Methods</summary>

- `.ctor`
- `Serialize`
- `Deserialize`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | ____keyMapping | MessagePack.Internal.AutomataDictionary |
| 24 | ____stringByteKeys | System.Byte[][] |

</details>


### `Gallop.MsgPack.Formatters.AccountChainDisconnectResponseFormatter` — score 35
*methods: deserialize, serialize; MsgPack formatter*

<details><summary>Methods</summary>

- `.ctor`
- `Serialize`
- `Deserialize`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | ____keyMapping | MessagePack.Internal.AutomataDictionary |
| 24 | ____stringByteKeys | System.Byte[][] |

</details>


### `Gallop.MsgPack.Formatters.AccountChainDisconnectResponse_CommonResponseFormatter` — score 35
*methods: deserialize, serialize; MsgPack formatter*

<details><summary>Methods</summary>

- `.ctor`
- `Serialize`
- `Deserialize`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | ____keyMapping | MessagePack.Internal.AutomataDictionary |
| 24 | ____stringByteKeys | System.Byte[][] |

</details>


### `Gallop.MsgPack.Formatters.AccountDeletionCancelRequestFormatter` — score 35
*methods: deserialize, serialize; MsgPack formatter*

<details><summary>Methods</summary>

- `.ctor`
- `Serialize`
- `Deserialize`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | ____keyMapping | MessagePack.Internal.AutomataDictionary |
| 24 | ____stringByteKeys | System.Byte[][] |

</details>


### `Gallop.MsgPack.Formatters.AccountDeletionCancelResponseFormatter` — score 35
*methods: deserialize, serialize; MsgPack formatter*

<details><summary>Methods</summary>

- `.ctor`
- `Serialize`
- `Deserialize`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | ____keyMapping | MessagePack.Internal.AutomataDictionary |
| 24 | ____stringByteKeys | System.Byte[][] |

</details>


### `Gallop.MsgPack.Formatters.AccountDeletionCancelResponse_CommonResponseFormatter` — score 35
*methods: deserialize, serialize; MsgPack formatter*

<details><summary>Methods</summary>

- `.ctor`
- `Serialize`
- `Deserialize`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | ____keyMapping | MessagePack.Internal.AutomataDictionary |
| 24 | ____stringByteKeys | System.Byte[][] |

</details>


### `Gallop.MsgPack.Formatters.AccountDeletionRequestRequestFormatter` — score 35
*methods: deserialize, serialize; MsgPack formatter*

<details><summary>Methods</summary>

- `.ctor`
- `Serialize`
- `Deserialize`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | ____keyMapping | MessagePack.Internal.AutomataDictionary |
| 24 | ____stringByteKeys | System.Byte[][] |

</details>


### `Gallop.MsgPack.Formatters.AccountDeletionRequestResponseFormatter` — score 35
*methods: deserialize, serialize; MsgPack formatter*

<details><summary>Methods</summary>

- `.ctor`
- `Serialize`
- `Deserialize`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | ____keyMapping | MessagePack.Internal.AutomataDictionary |
| 24 | ____stringByteKeys | System.Byte[][] |

</details>


### `Gallop.MsgPack.Formatters.AccountDeletionRequestResponse_CommonResponseFormatter` — score 35
*methods: deserialize, serialize; MsgPack formatter*

<details><summary>Methods</summary>

- `.ctor`
- `Serialize`
- `Deserialize`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | ____keyMapping | MessagePack.Internal.AutomataDictionary |
| 24 | ____stringByteKeys | System.Byte[][] |

</details>


### `Gallop.MsgPack.Formatters.AccountSteamChainDisconnectRequestFormatter` — score 35
*methods: deserialize, serialize; MsgPack formatter*

<details><summary>Methods</summary>

- `.ctor`
- `Serialize`
- `Deserialize`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | ____keyMapping | MessagePack.Internal.AutomataDictionary |
| 24 | ____stringByteKeys | System.Byte[][] |

</details>


### `Gallop.MsgPack.Formatters.AccountSteamChainDisconnectResponseFormatter` — score 35
*methods: deserialize, serialize; MsgPack formatter*

<details><summary>Methods</summary>

- `.ctor`
- `Serialize`
- `Deserialize`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | ____keyMapping | MessagePack.Internal.AutomataDictionary |
| 24 | ____stringByteKeys | System.Byte[][] |

</details>


### `Gallop.MsgPack.Formatters.AccountSteamChainDisconnectResponse_CommonResponseFormatter` — score 35
*methods: deserialize, serialize; MsgPack formatter*

<details><summary>Methods</summary>

- `.ctor`
- `Serialize`
- `Deserialize`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | ____keyMapping | MessagePack.Internal.AutomataDictionary |
| 24 | ____stringByteKeys | System.Byte[][] |

</details>


### `Gallop.MsgPack.Formatters.AddedGachaStockInfoFormatter` — score 35
*methods: deserialize, serialize; MsgPack formatter*

<details><summary>Methods</summary>

- `.ctor`
- `Serialize`
- `Deserialize`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | ____keyMapping | MessagePack.Internal.AutomataDictionary |
| 24 | ____stringByteKeys | System.Byte[][] |

</details>


### `Gallop.MsgPack.Formatters.AddMatchPointDataFormatter` — score 35
*methods: deserialize, serialize; MsgPack formatter*

<details><summary>Methods</summary>

- `.ctor`
- `Serialize`
- `Deserialize`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | ____keyMapping | MessagePack.Internal.AutomataDictionary |
| 24 | ____stringByteKeys | System.Byte[][] |

</details>


### `Gallop.MsgPack.Formatters.AppAnnounceFormatter` — score 35
*methods: deserialize, serialize; MsgPack formatter*

<details><summary>Methods</summary>

- `.ctor`
- `Serialize`
- `Deserialize`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | ____keyMapping | MessagePack.Internal.AutomataDictionary |
| 24 | ____stringByteKeys | System.Byte[][] |

</details>


### `Gallop.MsgPack.Formatters.BannerUrlRequestFormatter` — score 35
*methods: deserialize, serialize; MsgPack formatter*

<details><summary>Methods</summary>

- `.ctor`
- `Serialize`
- `Deserialize`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | ____keyMapping | MessagePack.Internal.AutomataDictionary |
| 24 | ____stringByteKeys | System.Byte[][] |

</details>


### `Gallop.MsgPack.Formatters.BannerUrlResponseFormatter` — score 35
*methods: deserialize, serialize; MsgPack formatter*

<details><summary>Methods</summary>

- `.ctor`
- `Serialize`
- `Deserialize`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | ____keyMapping | MessagePack.Internal.AutomataDictionary |
| 24 | ____stringByteKeys | System.Byte[][] |

</details>


### `Gallop.MsgPack.Formatters.BannerUrlResponse_CommonResponseFormatter` — score 35
*methods: deserialize, serialize; MsgPack formatter*

<details><summary>Methods</summary>

- `.ctor`
- `Serialize`
- `Deserialize`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | ____keyMapping | MessagePack.Internal.AutomataDictionary |
| 24 | ____stringByteKeys | System.Byte[][] |

</details>


### `Gallop.MsgPack.Formatters.BestRankInfoFormatter` — score 35
*methods: deserialize, serialize; MsgPack formatter*

<details><summary>Methods</summary>

- `.ctor`
- `Serialize`
- `Deserialize`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | ____keyMapping | MessagePack.Internal.AutomataDictionary |
| 24 | ____stringByteKeys | System.Byte[][] |

</details>


### `Gallop.MsgPack.Formatters.CabinedAccountGetMailInfoRequestFormatter` — score 35
*methods: deserialize, serialize; MsgPack formatter*

<details><summary>Methods</summary>

- `.ctor`
- `Serialize`
- `Deserialize`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | ____keyMapping | MessagePack.Internal.AutomataDictionary |
| 24 | ____stringByteKeys | System.Byte[][] |

</details>


### `Gallop.MsgPack.Formatters.CabinedAccountGetMailInfoResponseFormatter` — score 35
*methods: deserialize, serialize; MsgPack formatter*

<details><summary>Methods</summary>

- `.ctor`
- `Serialize`
- `Deserialize`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | ____keyMapping | MessagePack.Internal.AutomataDictionary |
| 24 | ____stringByteKeys | System.Byte[][] |

</details>


### `Gallop.MsgPack.Formatters.CabinedAccountGetMailInfoResponse_CommonResponseFormatter` — score 35
*methods: deserialize, serialize; MsgPack formatter*

<details><summary>Methods</summary>

- `.ctor`
- `Serialize`
- `Deserialize`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | ____keyMapping | MessagePack.Internal.AutomataDictionary |
| 24 | ____stringByteKeys | System.Byte[][] |

</details>


### `Gallop.MsgPack.Formatters.CabinedAccountRegisterEmailAddressRequestFormatter` — score 35
*methods: deserialize, serialize; MsgPack formatter*

<details><summary>Methods</summary>

- `.ctor`
- `Serialize`
- `Deserialize`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | ____keyMapping | MessagePack.Internal.AutomataDictionary |
| 24 | ____stringByteKeys | System.Byte[][] |

</details>


### `Gallop.MsgPack.Formatters.CabinedAccountRegisterEmailAddressResponseFormatter` — score 35
*methods: deserialize, serialize; MsgPack formatter*

<details><summary>Methods</summary>

- `.ctor`
- `Serialize`
- `Deserialize`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | ____keyMapping | MessagePack.Internal.AutomataDictionary |
| 24 | ____stringByteKeys | System.Byte[][] |

</details>


### `Gallop.MsgPack.Formatters.CabinedAccountRegisterEmailAddressResponse_CommonResponseFormatter` — score 35
*methods: deserialize, serialize; MsgPack formatter*

<details><summary>Methods</summary>

- `.ctor`
- `Serialize`
- `Deserialize`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | ____keyMapping | MessagePack.Internal.AutomataDictionary |
| 24 | ____stringByteKeys | System.Byte[][] |

</details>


### `Gallop.MsgPack.Formatters.CabinedAccountSendAuthCodeRequestFormatter` — score 35
*methods: deserialize, serialize; MsgPack formatter*

<details><summary>Methods</summary>

- `.ctor`
- `Serialize`
- `Deserialize`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | ____keyMapping | MessagePack.Internal.AutomataDictionary |
| 24 | ____stringByteKeys | System.Byte[][] |

</details>


### `Gallop.MsgPack.Formatters.CabinedAccountSendAuthCodeResponseFormatter` — score 35
*methods: deserialize, serialize; MsgPack formatter*

<details><summary>Methods</summary>

- `.ctor`
- `Serialize`
- `Deserialize`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | ____keyMapping | MessagePack.Internal.AutomataDictionary |
| 24 | ____stringByteKeys | System.Byte[][] |

</details>


### `Gallop.MsgPack.Formatters.CabinedAccountSendAuthCodeResponse_CommonResponseFormatter` — score 35
*methods: deserialize, serialize; MsgPack formatter*

<details><summary>Methods</summary>

- `.ctor`
- `Serialize`
- `Deserialize`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | ____keyMapping | MessagePack.Internal.AutomataDictionary |
| 24 | ____stringByteKeys | System.Byte[][] |

</details>


### `Gallop.MsgPack.Formatters.CabinedAccountSendVerificationUrlRequestFormatter` — score 35
*methods: deserialize, serialize; MsgPack formatter*

<details><summary>Methods</summary>

- `.ctor`
- `Serialize`
- `Deserialize`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | ____keyMapping | MessagePack.Internal.AutomataDictionary |
| 24 | ____stringByteKeys | System.Byte[][] |

</details>


### `Gallop.MsgPack.Formatters.CabinedAccountSendVerificationUrlResponseFormatter` — score 35
*methods: deserialize, serialize; MsgPack formatter*

<details><summary>Methods</summary>

- `.ctor`
- `Serialize`
- `Deserialize`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | ____keyMapping | MessagePack.Internal.AutomataDictionary |
| 24 | ____stringByteKeys | System.Byte[][] |

</details>


## MASTER_DATA (top 30 of 250)

### `Gallop.MasterCardRarityData.CardRarityData` — score 45
*fields: cardid, guts, speed, stamina; Master data*

<details><summary>Methods</summary>

- `.ctor`
- `get_Name`
- `get_Titlename`
- `get_Charaname`
- `get_CharaId`
- `GetProperDistanceShort`
- `GetProperDistanceMile`
- `GetProperDistanceMiddle`
- `GetProperDistanceLong`
- `GetProperDistanceType`
- `GetProperRunningStyleNige`
- `GetProperRunningStyleSenko`
- `GetProperRunningStyleSashi`
- `GetProperRunningStyleOikomi`
- `GetProperGroundTurf`
- `GetProperGroundDirt`
- `GetProperGroundType`
- `GetUniqueSkill`
- `GetBaseParam`
- `GetMaxParam`
- `GetMaxParameterDic`
- `GetMaxProperGroundType`
- `GetMaxProperDistanceType`
- `GetMaxProperRunningStyle`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | Id | System.Int32 |
| 20 | CardId | System.Int32 |
| 24 | Rarity | System.Int32 |
| 28 | RaceDressId | System.Int32 |
| 32 | SkillSet | System.Int32 |
| 36 | Speed | System.Int32 |
| 40 | Stamina | System.Int32 |
| 44 | Pow | System.Int32 |
| 48 | Guts | System.Int32 |
| 52 | Wiz | System.Int32 |
| 56 | MaxSpeed | System.Int32 |
| 60 | MaxStamina | System.Int32 |
| 64 | MaxPow | System.Int32 |
| 68 | MaxGuts | System.Int32 |
| 72 | MaxWiz | System.Int32 |
| 76 | ProperDistanceShort | System.Int32 |
| 80 | ProperDistanceMile | System.Int32 |
| 84 | ProperDistanceMiddle | System.Int32 |
| 88 | ProperDistanceLong | System.Int32 |
| 92 | ProperRunningStyleNige | System.Int32 |
| 96 | ProperRunningStyleSenko | System.Int32 |
| 100 | ProperRunningStyleSashi | System.Int32 |
| 104 | ProperRunningStyleOikomi | System.Int32 |
| 108 | ProperGroundTurf | System.Int32 |
| 112 | ProperGroundDirt | System.Int32 |
| 116 | GetDressId1 | System.Int32 |
| 120 | GetDressId2 | System.Int32 |
| 124 | _charaId | System.Int32 |

</details>


### `Gallop.MasterChallengeMatchBossNpc.ChallengeMatchBossNpc` — score 40
*fields: charaid, guts, speed, stamina; Master data*

<details><summary>Methods</summary>

- `.ctor`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | Id | System.Int32 |
| 20 | CharaId | System.Int32 |
| 24 | RaceDressId | System.Int32 |
| 28 | NicknameId | System.Int32 |
| 32 | CardRarityDataId | System.Int32 |
| 36 | Post | System.Int32 |
| 40 | Speed | System.Int32 |
| 44 | Stamina | System.Int32 |
| 48 | Pow | System.Int32 |
| 52 | Guts | System.Int32 |
| 56 | Wiz | System.Int32 |
| 60 | ProperDistanceShort | System.Int32 |
| 64 | ProperDistanceMile | System.Int32 |
| 68 | ProperDistanceMiddle | System.Int32 |
| 72 | ProperDistanceLong | System.Int32 |
| 76 | ProperRunningStyleNige | System.Int32 |
| 80 | ProperRunningStyleSenko | System.Int32 |
| 84 | ProperRunningStyleSashi | System.Int32 |
| 88 | ProperRunningStyleOikomi | System.Int32 |
| 92 | ProperGroundTurf | System.Int32 |
| 96 | ProperGroundDirt | System.Int32 |
| 100 | SkillSetId | System.Int32 |

</details>


### `Gallop.MasterSuccessionFactorEffect.SuccessionFactorEffect.FactorTargetType` — score 40
*fields: guts, power, speed, stamina; Master data*

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | value__ | System.Int32 |
| 0 | Balance | Gallop.MasterSuccessionFactorEffect.SuccessionFactorEffect.FactorTargetType |
| 0 | Speed | Gallop.MasterSuccessionFactorEffect.SuccessionFactorEffect.FactorTargetType |
| 0 | Stamina | Gallop.MasterSuccessionFactorEffect.SuccessionFactorEffect.FactorTargetType |
| 0 | Power | Gallop.MasterSuccessionFactorEffect.SuccessionFactorEffect.FactorTargetType |
| 0 | Guts | Gallop.MasterSuccessionFactorEffect.SuccessionFactorEffect.FactorTargetType |
| 0 | Wiz | Gallop.MasterSuccessionFactorEffect.SuccessionFactorEffect.FactorTargetType |
| 0 | Turf | Gallop.MasterSuccessionFactorEffect.SuccessionFactorEffect.FactorTargetType |
| 0 | Dirt | Gallop.MasterSuccessionFactorEffect.SuccessionFactorEffect.FactorTargetType |
| 0 | Nige | Gallop.MasterSuccessionFactorEffect.SuccessionFactorEffect.FactorTargetType |
| 0 | Senko | Gallop.MasterSuccessionFactorEffect.SuccessionFactorEffect.FactorTargetType |
| 0 | Sashi | Gallop.MasterSuccessionFactorEffect.SuccessionFactorEffect.FactorTargetType |
| 0 | Oikomi | Gallop.MasterSuccessionFactorEffect.SuccessionFactorEffect.FactorTargetType |
| 0 | Short | Gallop.MasterSuccessionFactorEffect.SuccessionFactorEffect.FactorTargetType |
| 0 | Mile | Gallop.MasterSuccessionFactorEffect.SuccessionFactorEffect.FactorTargetType |
| 0 | Middle | Gallop.MasterSuccessionFactorEffect.SuccessionFactorEffect.FactorTargetType |
| 0 | Long | Gallop.MasterSuccessionFactorEffect.SuccessionFactorEffect.FactorTargetType |
| 0 | Skill | Gallop.MasterSuccessionFactorEffect.SuccessionFactorEffect.FactorTargetType |
| 0 | MatchBonus | Gallop.MasterSuccessionFactorEffect.SuccessionFactorEffect.FactorTargetType |

</details>


### `Gallop.MasterCharacterSystemLottery.CharacterSystemLottery` — score 24
*fields: cardid, charaid; Master data*

<details><summary>Methods</summary>

- `.ctor`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | Id | System.Int32 |
| 20 | CharaId | System.Int32 |
| 24 | CardId | System.Int32 |
| 28 | CardRarityId | System.Int32 |
| 32 | Trigger | System.Int32 |
| 36 | Param1 | System.Int32 |
| 40 | Per | System.Int32 |
| 44 | Priority | System.Int32 |
| 48 | SysTextId | System.Int32 |

</details>


### `Gallop.MasterCardData.CardData` — score 21
*fields: charaid; Master data*

<details><summary>Methods</summary>

- `.ctor`
- `get_Name`
- `get_Titlename`
- `get_Charaname`
- `get_CharaFurigana`
- `get_IsDummyCard`
- `get_DefaultRarityData`
- `GetTalentParamDic`
- `GetTalentParamCalcDic`
- `GetHavePieceNum`
- `GetNeedForReleasePieceNum`
- `GetDefaultMasterRarityData`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | Id | System.Int32 |
| 20 | CharaId | System.Int32 |
| 24 | DefaultRarity | System.Int32 |
| 28 | LimitedChara | System.Int32 |
| 32 | AvailableSkillSetId | System.Int32 |
| 36 | TalentSpeed | System.Int32 |
| 40 | TalentStamina | System.Int32 |
| 44 | TalentPow | System.Int32 |
| 48 | TalentGuts | System.Int32 |
| 52 | TalentWiz | System.Int32 |
| 56 | TalentGroupId | System.Int32 |
| 60 | BgId | System.Int32 |
| 64 | GetPieceId | System.Int32 |
| 68 | RunningStyle | System.Int32 |

</details>


### `Gallop.MasterDressData.DressData` — score 21
*fields: charaid; Master data*

<details><summary>Methods</summary>

- `.ctor`
- `get_Name`
- `get_MainColor`
- `get_SubColor`
- `get_IsChangeByGender`
- `get_GetCondition`
- `IsBaseColorDress`
- `IsInTerm`
- `IsExclusive`
- `IsNormalDress`
- `IsSpecialSwimsuit`
- `GetBodyPartsID`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | Id | System.Int32 |
| 20 | ConditionType | System.Int32 |
| 24 | HaveMini | System.Boolean |
| 28 | GeneralPurpose | System.Int32 |
| 32 | CostumeType | System.Int32 |
| 36 | CharaId | System.Int32 |
| 40 | UseGender | System.Int32 |
| 44 | BodyShape | System.Int32 |
| 48 | BodyType | System.Int32 |
| 52 | BodyTypeSub | System.Int32 |
| 56 | BodySetting | System.Int32 |
| 60 | UseRace | System.Int32 |
| 64 | UseLive | System.Int32 |
| 68 | UseLiveTheater | System.Int32 |
| 72 | UseHome | System.Int32 |
| 76 | UseDressChange | System.Int32 |
| 80 | IsWet | System.Int32 |
| 84 | IsDirt | System.Int32 |
| 88 | HeadSubId | System.Int32 |
| 92 | UseSeason | System.Int32 |
| 96 | DressColorMain | System.String |
| 104 | DressColorSub | System.String |
| 112 | ColorNum | System.Int32 |
| 116 | DispOrder | System.Int32 |
| 120 | TailModelId | System.Int32 |
| 124 | TailModelSubId | System.Int32 |
| 128 | StartTime | System.Int64 |
| 136 | EndTime | System.Int64 |
| 0 | DRESS_CHANGE_GENDER_PARAM | System.Int32 |
| 144 | _getCondition | Gallop.MasterDressData.GetCondition |

</details>


### `Gallop.MasterSupportCardData.SupportCardData` — score 21
*fields: charaid; Master data*

<details><summary>Methods</summary>

- `.ctor`
- `get_Name`
- `get_Titlename`
- `get_Charaname`
- `get_CharaNameFurigana`
- `get_GroupName`
- `get_Story`
- `get_IsFriendSupportCard`
- `get_IsGroupSupportCard`
- `get_IsCharaSupportCard`
- `GetBestTraining`
- `IsAvailable`
- `GetMasterSupportCardGroupList`
- `GetGroupCharaIdList`
- `ContainsGroupSupportCard`
- `GetCharaIdList`
- `GetRestrictScenarioIdList`
- `CanUseScenario`
- `CanJoinDeckGroupSupportCard`
- `<CanJoinDeckGroupSupportCard>b__45_1`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | Id | System.Int32 |
| 20 | CharaId | System.Int32 |
| 24 | Rarity | System.Int32 |
| 28 | ExchangeItemId | System.Int32 |
| 32 | EffectTableId | System.Int32 |
| 36 | UniqueEffectId | System.Int32 |
| 40 | CommandType | System.Int32 |
| 44 | CommandId | System.Int32 |
| 48 | SupportCardType | System.Int32 |
| 52 | SkillSetId | System.Int32 |
| 56 | DetailPosX | System.Int32 |
| 60 | DetailPosY | System.Int32 |
| 64 | DetailScale | System.Int32 |
| 68 | DetailRotZ | System.Int32 |
| 72 | StartDate | System.Int64 |
| 80 | OutingMax | System.Int32 |
| 84 | EffectId | System.Int32 |
| 88 | _charaIdListCache | System.Collections.Generic.List<System.Int32> |

</details>


### `Gallop.MasterChampionsStandMotion.ChampionsStandMotion` — score 21
*fields: charaid; Master data*

<details><summary>Methods</summary>

- `.ctor`
- `get_IsRaceDressId`
- `get_IsMotionSet`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | CharaId | System.Int32 |
| 20 | Type | System.Int32 |
| 24 | RaceDressId | System.Int32 |
| 28 | MotionSet | System.Int32 |

</details>


### `Gallop.MasterFanRaidData.FanRaidData` — score 21
*fields: charaid; Master data*

<details><summary>Methods</summary>

- `.ctor`
- `get_StartDateTime`
- `get_CalcStartDateTime`
- `get_CalcEndDateTime`
- `get_EndDateTime`
- `get_IsEventInSession`
- `get_IsEventCalculating`
- `get_IsEventRewardReceiving`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | FanRaidId | System.Int32 |
| 20 | ConditionType | System.Byte |
| 21 | ConditionValue | System.Byte |
| 24 | CharaId | System.Int32 |
| 28 | DressId | System.Int32 |
| 32 | ResultSeCueName | System.String |
| 40 | ResultSeCuesheetName | System.String |
| 48 | StartDate | System.Int64 |
| 56 | CalcStartDate | System.Int64 |
| 64 | CalcEndDate | System.Int64 |
| 72 | EndDate | System.Int64 |

</details>


### `Gallop.MasterHomeEat.HomeEat` — score 21
*fields: charaid; Master data*

<details><summary>Methods</summary>

- `.ctor`
- `GetEatFacialMotionPath`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | CharaId | System.Int32 |
| 20 | BodyShape | System.Int32 |
| 24 | PropIdRight | System.Int32 |
| 32 | PropEatAnimationRight | System.String |
| 40 | OverrideMotionRight | System.String |
| 48 | PropIdLeft | System.Int32 |
| 56 | PropEatAnimationLeft | System.String |
| 64 | OverrideMotionLeft | System.String |
| 72 | WalkMotion | System.String |
| 80 | WalkCharaFaceType | System.String |
| 88 | EatMotion | System.String |
| 96 | EatFacialMotion | System.String |
| 104 | Odds | System.Int32 |

</details>


### `Gallop.MasterTeamBuildingCollectionChara.TeamBuildingCollectionChara` — score 21
*fields: charaid; Master data*

<details><summary>Methods</summary>

- `.ctor`
- `GetBonusDataList`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | Id | System.Int32 |
| 20 | TeamBuildingEventId | System.Int32 |
| 24 | CharaId | System.Int32 |
| 28 | ConditionType1 | System.Byte |
| 29 | BonusType1 | System.Byte |
| 32 | BonusValue1 | System.Int32 |
| 36 | ConditionType2 | System.Byte |
| 37 | BonusType2 | System.Byte |
| 40 | BonusValue2 | System.Int32 |
| 48 | _bonusDataList | System.Collections.Generic.List<Gallop.MasterTeamBuildingCollectionChara.BonusData> |

</details>


### `Gallop.MasterCharaCategoryMotion.CharaCategoryMotion` — score 16
*fields: charaid; Master data*

<details><summary>Methods</summary>

- `.ctor`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | CharaId | System.Int32 |
| 20 | StandbyMotion1 | System.Int32 |
| 24 | StandbyMotion2 | System.Int32 |
| 28 | StandbyMotion3 | System.Int32 |
| 32 | StandbyMotion4 | System.Int32 |
| 36 | StandbyMotion5 | System.Int32 |
| 40 | StandbyMotion6 | System.Int32 |

</details>


### `Gallop.MasterCharaMotionAct.CharaMotionAct` — score 16
*fields: charaid; Master data*

<details><summary>Methods</summary>

- `.ctor`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | Id | System.Int32 |
| 20 | CharaId | System.Int32 |
| 24 | TargetMotion | System.Int32 |
| 32 | CommandName | System.String |

</details>


### `Gallop.MasterCharaType.CharaType` — score 16
*fields: charaid; Master data*

<details><summary>Methods</summary>

- `.ctor`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | Id | System.String |
| 24 | CharaId | System.Int32 |
| 28 | TargetScene | System.Int32 |
| 32 | TargetCut | System.Int32 |
| 36 | TargetType | System.Int32 |
| 40 | Value | System.Int32 |

</details>


### `Gallop.MasterFacialMouthChange.FacialMouthChange` — score 16
*fields: charaid; Master data*

<details><summary>Methods</summary>

- `.ctor`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | Id | System.Int32 |
| 20 | CharaId | System.Int32 |
| 24 | BeforeFacialname | System.String |
| 32 | AfterFacialname | System.String |

</details>


### `Gallop.MasterSupportCardGroup.SupportCardGroup` — score 16
*fields: charaid; Master data*

<details><summary>Methods</summary>

- `.ctor`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | Id | System.Int32 |
| 20 | SupportCardId | System.Int32 |
| 24 | CharaId | System.Int32 |
| 28 | OutingMax | System.Int32 |

</details>


### `Gallop.MasterChampionsNewsCharaComment.ChampionsNewsCharaComment` — score 16
*fields: charaid; Master data*

<details><summary>Methods</summary>

- `.ctor`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | Id | System.Int32 |
| 20 | RoundId | System.Int32 |
| 24 | CharaId | System.Int32 |
| 28 | BigFlag | System.Int32 |

</details>


### `Gallop.MasterChampionsNewsCharaDetail.ChampionsNewsCharaDetail` — score 16
*fields: charaid; Master data*

<details><summary>Methods</summary>

- `.ctor`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | Id | System.Int32 |
| 20 | CharaTextGroup | System.Int32 |
| 24 | TextNumber | System.Int32 |
| 28 | ResourceId | System.Int32 |
| 32 | CharaId | System.Int32 |
| 36 | SingleWin | System.Int32 |
| 40 | NicknameId | System.Int32 |
| 44 | ParameterType | System.Int32 |
| 48 | ParameterMin | System.Int32 |
| 52 | RunningStyle | System.Int32 |
| 56 | ProperRunningStyleMin | System.Int32 |

</details>


### `Gallop.MasterChampionsNewsWinComment.ChampionsNewsWinComment` — score 16
*fields: charaid; Master data*

<details><summary>Methods</summary>

- `.ctor`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | Id | System.Int32 |
| 20 | RoundId | System.Int32 |
| 24 | CharaId | System.Int32 |
| 28 | BigFlag | System.Int32 |

</details>


### `Gallop.MasterFanRaidBonusChara.FanRaidBonusChara` — score 16
*fields: charaid; Master data*

<details><summary>Methods</summary>

- `.ctor`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | Id | System.Int32 |
| 20 | FanRaidId | System.Int32 |
| 24 | CharaId | System.Int32 |
| 28 | AddFan | System.Int32 |

</details>


### `Gallop.MasterFanRaidTopChara.FanRaidTopChara` — score 16
*fields: charaid; Master data*

<details><summary>Methods</summary>

- `.ctor`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | Id | System.Int32 |
| 20 | TopDataId | System.Int32 |
| 24 | CharaId | System.Int32 |
| 28 | DressId | System.Int32 |
| 32 | MiniMotionId | System.Int32 |

</details>


### `Gallop.MasterJukeboxCharaTagData.JukeboxCharaTagData` — score 16
*fields: charaid; Master data*

<details><summary>Methods</summary>

- `.ctor`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | Id | System.Int32 |
| 20 | CharaId | System.Int32 |
| 24 | Tag | System.Int32 |
| 32 | StartDate | System.Int64 |
| 40 | EndDate | System.Int64 |

</details>


### `Gallop.MasterJukeboxComment.JukeboxComment` — score 16
*fields: charaid; Master data*

<details><summary>Methods</summary>

- `.ctor`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | Id | System.Int32 |
| 20 | CommentId | System.Int32 |
| 24 | CharaId | System.Int32 |
| 28 | CommentType | System.Int32 |
| 32 | VariationType | System.Int32 |
| 36 | VariationValue | System.Int32 |

</details>


### `Gallop.MasterJukeboxReactionData.JukeboxReactionData` — score 16
*fields: charaid; Master data*

<details><summary>Methods</summary>

- `.ctor`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | Id | System.Int32 |
| 20 | CharaId | System.Int32 |
| 24 | ReactionCharaId | System.Int32 |
| 32 | StartDate | System.Int64 |
| 40 | EndDate | System.Int64 |

</details>


### `Gallop.MasterLivePermissionData.LivePermissionData` — score 16
*fields: charaid; Master data*

<details><summary>Methods</summary>

- `.ctor`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | MusicId | System.Int32 |
| 20 | CharaId | System.Int32 |

</details>


### `Gallop.MasterNoteProfile.NoteProfile` — score 16
*fields: charaid; Master data*

<details><summary>Methods</summary>

- `.ctor`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | Id | System.Int32 |
| 20 | CharaId | System.Int32 |
| 24 | TextType | System.Int32 |
| 28 | LockType | System.Int32 |
| 32 | LockValue | System.Int32 |
| 36 | SecretFlg | System.Int32 |
| 40 | Sort | System.Int32 |

</details>


### `Gallop.MasterSuccessionRelationMember.SuccessionRelationMember` — score 16
*fields: charaid; Master data*

<details><summary>Methods</summary>

- `.ctor`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | Id | System.Int32 |
| 20 | RelationType | System.Int32 |
| 24 | CharaId | System.Int32 |

</details>


### `Gallop.MasterTeamBuildingCharaGroup.TeamBuildingCharaGroup` — score 16
*fields: charaid; Master data*

<details><summary>Methods</summary>

- `.ctor`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | Id | System.Int32 |
| 20 | CharaGroupId | System.Int32 |
| 24 | CharaId | System.Int32 |

</details>


### `Gallop.MasterTeamBuildingCollectionSet.TeamBuildingCollectionSet` — score 16
*fields: skillid; Master data*

<details><summary>Methods</summary>

- `.ctor`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | Id | System.Int32 |
| 20 | TeamBuildingEventId | System.Int32 |
| 24 | CharaGroupId | System.Int32 |
| 28 | SkillId | System.Int32 |

</details>


### `Gallop.MasterAudioCuesheet` — score 13
*Master data*

<details><summary>Methods</summary>

- `.ctor`
- `Get`
- `_SelectOne`
- `GetWithAttribute`
- `_SelectWithAttribute`
- `GetListWithAttribute`
- `MaybeListWithAttribute`
- `_ListSelectWithAttribute`
- `_CreateOrmByQueryResultWithAttribute`
- `Unload`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 0 | TABLE_NAME | System.String |
| 16 | _db | Gallop.MasterAudioDatabase |
| 24 | _notFounds | System.Collections.Generic.HashSet<System.Int32> |
| 32 | _lazyPrimaryKeyDictionary | System.Collections.Generic.Dictionary<System.Int32,Gallop.MasterAudioCuesheet.AudioCuesheet> |
| 40 | _dictionaryWithAttribute | System.Collections.Generic.Dictionary<System.Int32,System.Collections.Generic.List<Gallop.MasterAudioCuesheet.AudioCuesheet>> |

</details>


## COMMENTARY (top 21 of 21)

### `Gallop.JikkyoTrigger.Command` — score 24
*fields: charaid, distance, weather*

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | value__ | System.Int32 |
| 0 | None | Gallop.JikkyoTrigger.Command |
| 0 | NoPlayer | Gallop.JikkyoTrigger.Command |
| 0 | Weather | Gallop.JikkyoTrigger.Command |
| 0 | Course | Gallop.JikkyoTrigger.Command |
| 0 | Race | Gallop.JikkyoTrigger.Command |
| 0 | Grade | Gallop.JikkyoTrigger.Command |
| 0 | Ground | Gallop.JikkyoTrigger.Command |
| 0 | GroundCondition | Gallop.JikkyoTrigger.Command |
| 0 | CourseDis | Gallop.JikkyoTrigger.Command |
| 0 | Popularity | Gallop.JikkyoTrigger.Command |
| 0 | Order | Gallop.JikkyoTrigger.Command |
| 0 | BackOrder | Gallop.JikkyoTrigger.Command |
| 0 | Lane | Gallop.JikkyoTrigger.Command |
| 0 | LaneDiff | Gallop.JikkyoTrigger.Command |
| 0 | Length | Gallop.JikkyoTrigger.Command |
| 0 | RunStyle | Gallop.JikkyoTrigger.Command |
| 0 | GoodStart | Gallop.JikkyoTrigger.Command |
| 0 | BadStart | Gallop.JikkyoTrigger.Command |
| 0 | TopMember | Gallop.JikkyoTrigger.Command |
| 0 | BagunLen | Gallop.JikkyoTrigger.Command |
| 0 | RankChange | Gallop.JikkyoTrigger.Command |
| 0 | TimeSpeedChange | Gallop.JikkyoTrigger.Command |
| 0 | TimeRankChange | Gallop.JikkyoTrigger.Command |
| 0 | Between | Gallop.JikkyoTrigger.Command |
| 0 | DistanceApproach | Gallop.JikkyoTrigger.Command |
| 0 | DistanceAway | Gallop.JikkyoTrigger.Command |
| 0 | FinalRank | Gallop.JikkyoTrigger.Command |
| 0 | Block | Gallop.JikkyoTrigger.Command |
| 0 | NonTemptationTime | Gallop.JikkyoTrigger.Command |
| 0 | LastCorner | Gallop.JikkyoTrigger.Command |
| 0 | Skill | Gallop.JikkyoTrigger.Command |
| 0 | HPRate | Gallop.JikkyoTrigger.Command |
| 0 | TopGroupExist | Gallop.JikkyoTrigger.Command |
| 0 | CharaID | Gallop.JikkyoTrigger.Command |
| 0 | JikkyoMode | Gallop.JikkyoTrigger.Command |
| 0 | NoSelect | Gallop.JikkyoTrigger.Command |
| 0 | LaneDistance | Gallop.JikkyoTrigger.Command |
| 0 | RankHigher | Gallop.JikkyoTrigger.Command |
| 0 | BlockMotion | Gallop.JikkyoTrigger.Command |
| 0 | SkillExtension | Gallop.JikkyoTrigger.Command |
| 0 | Event_Distance | Gallop.JikkyoTrigger.Command |
| 0 | Event_Corner | Gallop.JikkyoTrigger.Command |
| 0 | Event_Param | Gallop.JikkyoTrigger.Command |
| 0 | RaceIdRange | Gallop.JikkyoTrigger.Command |
| 0 | LastSpurt | Gallop.JikkyoTrigger.Command |
| 0 | CourseAround | Gallop.JikkyoTrigger.Command |
| 0 | ClothType | Gallop.JikkyoTrigger.Command |
| 0 | SkillReceived | Gallop.JikkyoTrigger.Command |
| 0 | HorseNum | Gallop.JikkyoTrigger.Command |
| 0 | GroundChange | Gallop.JikkyoTrigger.Command |
| 0 | DistanceToLastCorner | Gallop.JikkyoTrigger.Command |
| 0 | CornerBefore | Gallop.JikkyoTrigger.Command |
| 0 | CornerJust | Gallop.JikkyoTrigger.Command |
| 0 | CornerAfter | Gallop.JikkyoTrigger.Command |
| 0 | SkillCutinPrev | Gallop.JikkyoTrigger.Command |
| 0 | Distance | Gallop.JikkyoTrigger.Command |
| 0 | NpcType | Gallop.JikkyoTrigger.Command |
| 0 | Temptation | Gallop.JikkyoTrigger.Command |
| 0 | LastBaseId | Gallop.JikkyoTrigger.Command |
| 0 | RelativeSpeed | Gallop.JikkyoTrigger.Command |
| 0 | OrderOneAfterAnother | Gallop.JikkyoTrigger.Command |
| 0 | InterruptOrderChange | Gallop.JikkyoTrigger.Command |
| 0 | FinishLength | Gallop.JikkyoTrigger.Command |
| 0 | ParamSpeedRank | Gallop.JikkyoTrigger.Command |
| 0 | ParamStaminaRank | Gallop.JikkyoTrigger.Command |
| 0 | ParamPowerRank | Gallop.JikkyoTrigger.Command |
| 0 | ParamGutsRank | Gallop.JikkyoTrigger.Command |
| 0 | ParamWizRank | Gallop.JikkyoTrigger.Command |
| 0 | PlayerTemptation | Gallop.JikkyoTrigger.Command |
| 0 | SkillActivate | Gallop.JikkyoTrigger.Command |
| 0 | NOUSE_01 | Gallop.JikkyoTrigger.Command |
| 0 | StaminaZeroDistance | Gallop.JikkyoTrigger.Command |
| 0 | JikkyoActorId | Gallop.JikkyoTrigger.Command |
| 0 | CommentActorId | Gallop.JikkyoTrigger.Command |
| 0 | MainParamRank | Gallop.JikkyoTrigger.Command |
| 0 | StaminaZeroHorseNum | Gallop.JikkyoTrigger.Command |
| 0 | RelativeSpeedHorseNum | Gallop.JikkyoTrigger.Command |
| 0 | Positioning | Gallop.JikkyoTrigger.Command |
| 0 | CompareDistance | Gallop.JikkyoTrigger.Command |
| 0 | HomeStraight | Gallop.JikkyoTrigger.Command |
| 0 | BackStraight | Gallop.JikkyoTrigger.Command |
| 0 | WinnerStandFirstTime | Gallop.JikkyoTrigger.Command |
| 0 | UpdateCurHorse | Gallop.JikkyoTrigger.Command |
| 0 | Time | Gallop.JikkyoTrigger.Command |
| 0 | SingleModeDegreeType | Gallop.JikkyoTrigger.Command |
| 0 | WinSaddle | Gallop.JikkyoTrigger.Command |
| 0 | Undefeated | Gallop.JikkyoTrigger.Command |
| 0 | WinRace | Gallop.JikkyoTrigger.Command |
| 0 | NotWinRaceGroup1 | Gallop.JikkyoTrigger.Command |
| 0 | RaceGroup | Gallop.JikkyoTrigger.Command |
| 0 | RaceType | Gallop.JikkyoTrigger.Command |
| 0 | TeamStadiumPromotionType | Gallop.JikkyoTrigger.Command |
| 0 | TeamStadiumCurrentRound | Gallop.JikkyoTrigger.Command |
| 0 | TeamStadiumRoundResult | Gallop.JikkyoTrigger.Command |
| 0 | TeamStadiumWinCount | Gallop.JikkyoTrigger.Command |
| 0 | TeamStadiumScoreRecord | Gallop.JikkyoTrigger.Command |
| 0 | PopularityMarkRank | Gallop.JikkyoTrigger.Command |
| 0 | PopularityMarkRankTopCount | Gallop.JikkyoTrigger.Command |
| 0 | Motivation | Gallop.JikkyoTrigger.Command |
| 0 | DistanceType | Gallop.JikkyoTrigger.Command |
| 0 | ProperGround | Gallop.JikkyoTrigger.Command |
| 0 | ProperDistance | Gallop.JikkyoTrigger.Command |
| 0 | ProperRunningStyle | Gallop.JikkyoTrigger.Command |
| 0 | SingleModeWinCountGI | Gallop.JikkyoTrigger.Command |
| 0 | SingleModeNotWinGIRaceCourse | Gallop.JikkyoTrigger.Command |
| 0 | CharaIdEntry | Gallop.JikkyoTrigger.Command |
| 0 | SingleModeWinCountGrade | Gallop.JikkyoTrigger.Command |
| 0 | SingleModeEntryCountGrade | Gallop.JikkyoTrigger.Command |
| 0 | SingleModeWinCount | Gallop.JikkyoTrigger.Command |
| 0 | SingleModeTeamRaceCurrentRound | Gallop.JikkyoTrigger.Command |
| 0 | SingleModeTeamRaceRoundResult | Gallop.JikkyoTrigger.Command |
| 0 | SingleModeTeamRaceWinCount | Gallop.JikkyoTrigger.Command |
| 0 | SingleModeTeamRaceBossBattle | Gallop.JikkyoTrigger.Command |
| 0 | SingleModeTeamRaceHonor | Gallop.JikkyoTrigger.Command |
| 0 | SingleModeFreeRaceResult | Gallop.JikkyoTrigger.Command |
| 0 | SingleModeFreeTopPointDiff | Gallop.JikkyoTrigger.Command |
| 0 | SingleModeFreeTopAndSecondPointDiff | Gallop.JikkyoTrigger.Command |
| 0 | SingleModeFreeTotalPointRank | Gallop.JikkyoTrigger.Command |
| 0 | SingleModeScenarioId | Gallop.JikkyoTrigger.Command |
| 0 | SingleModePlayRaceInstanceId | Gallop.JikkyoTrigger.Command |

</details>


### `Gallop.JikkyoTrigger.FrameData` — score 16
*fields: distance, speed*

<details><summary>Methods</summary>

- `.ctor`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | time | System.Single |
| 24 | order | System.Int32[] |
| 32 | distance | System.Single[] |
| 40 | speed | System.Single[] |
| 48 | nonTemptationTime | System.Int32[] |

</details>


### `Gallop.JikkyoTagProcessor.OmitTagInfo` — score 8
*fields: charaid*

<details><summary>Methods</summary>

- `.ctor`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | Tag | System.String |
| 24 | CharaId | System.Int32 |
| 28 | HorseIndex | System.Int32 |
| 32 | IsOmitGroup | System.Boolean |

</details>


### `Gallop.JikkyoTagProcessor.CalledTag` — score 8
*fields: charaid*

<details><summary>Methods</summary>

- `.ctor`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | Tag | System.String |
| 24 | CharaId | System.Int32 |
| 28 | HorseIndex | System.Int32 |
| 32 | Group | System.Int32 |
| 36 | TimeFromCalled | System.Single |
| 40 | Tension | Gallop.Jikkyo.Tension |

</details>


### `Gallop.IJikkyoAccessor` — score 5
<details><summary>Methods</summary>

- `SetUp`
- `StartJikkyo`
- `SetJikkyoUpdateEnable`
- `SkipToStart`
- `SkipToLast`
- `UpdateJikkyou`
- `Pause`
- `Clear`
- `ClearVoice`
- `ClearReserve`
- `IsEndJikkyoGateIn`
- `IsEndJikkyoAfterGoal`
- `NotifyRaceGateOpen`

</details>


### `Gallop.Jikkyo` — score 5
<details><summary>Methods</summary>

- `get_SceneType`
- `get_NearGoalDistance`
- `get_NearGoalInterruptDisableDistance`
- `get_CommentDisableDistance`
- `.ctor`
- `GetFirstHorseDistance`
- `CreateTagProcessor`
- `SetUp`
- `Go`
- `NotifyRaceGateOpen`
- `SkipToStart`
- `SkipToLast`
- `IsEndJikkyoGateIn`
- `IsEndJikkyouAfterGoal`
- `get_IsCrossTimeEnable`
- `Exec`
- `IsNearGoal`
- `GetRaceRemain`
- `GetHorseIndexByOrder`
- `JikkyoExec`
- `AddSubMode`
- `UpdateSilentTime`
- `ChangeMode`
- `GetNextModeByEmpty`
- `GetNextModeByRaceState`
- `IsCommentEnable`
- `FirstExec`
- `PlayEventCamera`
- `GetEventCameraTargetHorseIndex`
- `GetEventCameraTargetHorseIndexOne`
- `IsOrderPlaying`
- `AddReserveInterruptOrder`
- `InvalidateNewLine`
- `get_CurrentSkillDetail`
- `get_CurrentSkillHorseInfo`
- `get_CurrentSkillTargetFlags`
- `get_CurrentSkillTargetNum`
- `get_CornerCountDict`
- `get_IsFixedResultBoard`
- `set_IsFixedResultBoard`
- `InitRaceEvent`
- `CountBitFlags`
- `EventCallBack_Distance`
- `UpdateInterruptCorner`
- `UpdateInterruptCornerSub`
- `CheckInterruptCorner`
- `UpdateInterruptLastBaseId`
- `EventCallBack_CourseEvent`
- `UpdateInterruptPlayer`
- `ExecInterruptCmd`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 256 | _isRaceGateOpen | System.Boolean |
| 0 | TriggerNum | System.Int32 |
| 0 | SituationNone | System.Int32 |
| 0 | CourseParamGroundValueNum | System.Int32 |
| 0 | CourseParamGroundValueIndex | System.Int32 |
| 0 | CourseParamCornerNoIndex | System.Int32 |
| 0 | CourseParamCornerDistanceIndex | System.Int32 |
| 0 | CornerDefaultDistance | System.Single |
| 0 | CornerPrevOffsetDistance | System.Single |
| 0 | CornerBeforeRatio | System.Single |
| 0 | CornerJustRatio | System.Single |
| 264 | _currentSkillDetail | Gallop.ISkillDetail |
| 272 | _currentSkillHorseInfo | Gallop.HorseRaceInfo |
| 280 | _currentSkillTargetFlags | System.Int32 |
| 284 | _currentSkillTargetNum | System.Int32 |
| 288 | _cornerCountDict | System.Collections.Generic.Dictionary<System.Int32,System.Int32> |
| 296 | _cornerEvents | Gallop.CourseEventManager.CourseEvent[] |
| 304 | _cornerEventCheckIndex | System.Int32 |
| 308 | _lastStraightRemainDistance | System.Single |
| 312 | _isFixedResultBoard | System.Boolean |
| 313 | _isPlayerTemptation | System.Boolean |

</details>


### `Gallop.JikkyoAccessorNull` — score 5
<details><summary>Methods</summary>

- `SetUp`
- `StartJikkyo`
- `SetJikkyoUpdateEnable`
- `SkipToStart`
- `SkipToLast`
- `UpdateJikkyou`
- `Pause`
- `Clear`
- `ClearVoice`
- `ClearReserve`
- `IsEndJikkyoGateIn`
- `IsEndJikkyoAfterGoal`
- `NotifyRaceGateOpen`
- `.ctor`

</details>


### `Gallop.JikkyoAccessorReplay` — score 5
<details><summary>Methods</summary>

- `.ctor`
- `SetUp`
- `StartJikkyo`
- `SetJikkyoUpdateEnable`
- `SkipToStart`
- `SkipToLast`
- `UpdateJikkyou`
- `Pause`
- `Clear`
- `ClearVoice`
- `ClearReserve`
- `IsEndJikkyoGateIn`
- `IsEndJikkyoAfterGoal`
- `NotifyRaceGateOpen`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | _jikkyo | Gallop.Jikkyo |
| 24 | _isEnableUpdate | System.Boolean |

</details>


### `Gallop.JikkyoControllerBase` — score 5
<details><summary>Methods</summary>

- `get_SilentTimeMaxSec`
- `get_ImmidiateSuspendTime`
- `get_SceneType`
- `get_IsExistPlayer`
- `get_CurMode`
- `get_LastBaseId`
- `set_LastBaseId`
- `get_JikkyoBaseCache`
- `get_CurrentSkillDetail`
- `get_CurrentSkillHorseInfo`
- `get_LastCornerNo`
- `set_LastCornerNo`
- `get_EventDistance`
- `set_EventDistance`
- `get_CourseEventParamValues`
- `set_CourseEventParamValues`
- `get_EventGroundChange`
- `set_EventGroundChange`
- `get_CornerCountDict`
- `get_CurrentSkillTargetFlags`
- `get_CurrentSkillTargetNum`
- `.ctor`
- `Release`
- `CreateTagProcessor`
- `ReplaceTag`
- `ReplaceSoundTag`
- `InitTag`
- `UpdateTagHorseRank`
- `UpdateTagByHorse`
- `SetTagBasin`
- `SetTagGoodStart`
- `SetTagBadStart`
- `SetUp`
- `Go`
- `Stop`
- `ClearDisplay`
- `ClearVoice`
- `Pause`
- `IsPause`
- `SetJikkyouTextController`
- `get_IsCrossTimeEnable`
- `CalcSentenceCrossTime`
- `Exec`
- `IsReserveSuspend`
- `SetReserveSuspend`
- `IsPlaySuspend`
- `SetPlaySuspend`
- `GetPlayerHorseInfo`
- `GetPlayerHorseIndex`
- `JikkyoExec`
- `GetJikkyoBaseListByMode`
- `AddSubMode`
- `IsSubModeLoop`
- `GetJikkyoBaseListBySituation`
- `AddSubSituation`
- `ResetSilentTime`
- `AddSilentTime`
- `UpdateSilentTime`
- `GetJikkyoBaseMaxPriority`
- `GetJikkyoBaseTotalPer`
- `LotJikkyoBaseWithPriority`
- `PickJikkyoBase`
- `CreateTriggerOK`
- `IsJikkyoTriggerOK`
- `LotMessage`
- `LotComment`
- `GetMessageTotalPer`
- `GetCommentTotalPer`
- `CheckPlayableMessage`
- `CheckPlayableComment`
- `OnMessageEnd`
- `HasPlayableJikkyoMessage`
- `HasPlayableJikkyoComment`
- `IsJikkyoPlaying`
- `GetRemainingPlayTime`
- `ChangeMode`
- `GetNextModeByEmpty`
- `GetFirstHorseDistance`
- `GetHorseIndexByOrder`
- `ChangeSituation`
- `AddReserve`
- `PopReserveInfo`
- `ReserveMessage`
- `ReserveComment`
- `IsCommentEnable`
- `ClearReserve`
- `ClearReserveExceptDiscard`
- `HasReserve`
- `GetAndRemoveReserveHead`
- `JikkyoReserveExec`
- `FirstExec`
- `ExecJikkyoPostProcess`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 0 | RESERVE_BUFFER_MAX | System.Int32 |
| 0 | REUSE_ID_NUM_MAX | System.Int32 |
| 0 | DISABLE_REUSE_ID_NUM_MAX | System.Int32 |
| 0 | DISABLE_REUSE_SITUATION_NUM_MAX | System.Int32 |
| 16 | _mode | Gallop.Jikkyo.Mode |
| 20 | _subMode | System.Int32 |
| 24 | _subModeMax | System.Int32 |
| 28 | _anytimeBackSubMode | System.Int32 |
| 32 | _situation | System.Int32 |
| 36 | _subSituation | System.Int32 |
| 40 | _subSituationMax | System.Int32 |
| 44 | _isPause | System.Boolean |
| 48 | _curReserveInfo | Gallop.JikkyoControllerBase.ReserveInfo |
| 56 | _curDisplayInfo | Gallop.JikkyoControllerBase.DisplayInfo |
| 64 | _reserveList | System.Collections.Generic.List<Gallop.JikkyoControllerBase.ReserveInfo> |
| 72 | _reserveInfoBuffer | Gallop.JikkyoControllerBase.ReserveInfo[] |
| 80 | _reserveInfoBufferIndex | System.Int32 |
| 84 | _reserveExecId | System.Int32 |
| 88 | _usedMessageIdList | System.Collections.Generic.List<System.Int32> |
| 96 | _usedCommentIdList | System.Collections.Generic.List<System.Int32> |
| 104 | _usedBaseIdList | System.Collections.Generic.List<System.Int32> |
| 112 | _usedSituationList | System.Collections.Generic.List<System.Int32> |
| 120 | _silentTime | System.Single |
| 124 | _reserveSuspendTime | System.Single |
| 128 | _playSuspendTime | System.Single |
| 132 | _isExistPlayer | System.Boolean |
| 136 | _jikkyoParam | Gallop.RaceParamDefine.JikkyoParam |
| 144 | _playingTension | Gallop.Jikkyo.Tension |
| 148 | <LastBaseId>k__BackingField | System.Int32 |
| 152 | _lastReservedType | Gallop.Jikkyo.JikkyoType |
| 156 | _lastReservedMessageId | System.Int32 |
| 160 | _lastBaseId | System.Int32 |
| 168 | _jikkyoBaseCache | Gallop.RaceJikkyoBaseCache |
| 176 | _jikkyoDisp | Gallop.JikkyoDisplay |
| 184 | _jikkyoTag | Gallop.JikkyoTagProcessor |
| 192 | _jikkyoTriggerCmd | Gallop.JikkyoTrigger |
| 200 | _jikkyoText | Gallop.JikkyouTextController |
| 208 | _tmpTriggerTrueList | System.Collections.Generic.List<Gallop.RaceJikkyoBaseElementCache> |
| 216 | <LastCornerNo>k__BackingField | System.Int32 |
| 220 | <EventDistance>k__BackingField | System.Int32 |
| 224 | <CourseEventParamValues>k__BackingField | System.Int32[] |
| 232 | <EventGroundChange>k__BackingField | Gallop.RaceDefine.GroundType |
| 240 | _horseAccessor | Gallop.IRaceHorseAccessor |
| 248 | _raceInfo | Gallop.RaceInfo |

</details>


### `Gallop.JikkyoControllerBase.DisplayInfo` — score 5
<details><summary>Methods</summary>

- `.ctor`
- `.cctor`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | type | Gallop.Jikkyo.JikkyoType |
| 20 | tension | Gallop.Jikkyo.Tension |
| 24 | text | System.String |
| 32 | voice | System.String |
| 40 | CalledTagList | System.Collections.Generic.List<Gallop.JikkyoTagProcessor.CalledTag> |
| 0 | DISPLAY_NULL | Gallop.JikkyoControllerBase.DisplayInfo |

</details>


### `Gallop.JikkyoControllerBase.ReserveInfo` — score 5
<details><summary>Methods</summary>

- `Initialize`
- `Setup`
- `Add`
- `.ctor`
- `.cctor`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | JikkyoBase | Gallop.RaceJikkyoBaseElementCache |
| 24 | DisplayInfoList | System.Collections.Generic.List<Gallop.JikkyoControllerBase.DisplayInfo> |
| 32 | _displayInfoBuffer | Gallop.JikkyoControllerBase.DisplayInfo[] |
| 40 | _displayInfoBufferIndex | System.Int32 |
| 0 | DISPLAY_MAX | System.Int32 |
| 44 | CurHorseIndex | System.Int32 |
| 48 | PickupHorseIndex | System.Int32 |
| 0 | RESERVE_NULL | Gallop.JikkyoControllerBase.ReserveInfo |

</details>


### `Gallop.JikkyoDisplay` — score 5
<details><summary>Methods</summary>

- `Update`
- `Play`
- `Clear`
- `ClearVoice`
- `IsPlayingText`
- `IsPlayingVoice`
- `GetRemainingTime`
- `GetVoiceLength`
- `GetVoicePlayTime`
- `GetVoiceRemainingTime`
- `GetTextRemainingTime`
- `CalcTextRemainTime`
- `Setup`
- `SetTextController`
- `Pause`
- `IsUseVoice`
- `.ctor`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | _jikkyouText | Gallop.JikkyouTextController |
| 24 | _jikkyoVoice | Gallop.JikkyoVoice |
| 32 | _onEnd | System.Action |
| 40 | _waitSecPerChar | System.Single |
| 44 | _waitSecMin | System.Single |
| 48 | _waitSecMax | System.Single |
| 52 | _textRemainTime | System.Single |
| 56 | _isPause | System.Boolean |

</details>


### `Gallop.JikkyoControllerPaddock` — score 5
<details><summary>Methods</summary>

- `get_SceneType`
- `get_CurrentSkillDetail`
- `get_CurrentSkillHorseInfo`
- `get_CornerCountDict`
- `get_CurrentSkillTargetFlags`
- `get_CurrentSkillTargetNum`
- `.ctor`
- `GetFirstHorseDistance`
- `CreateTagProcessor`
- `Go`
- `get_IsCrossTimeEnable`
- `Exec`
- `GetHorseIndexByOrder`
- `JikkyoExec`
- `ResetSubMode`
- `AddSubMode`
- `SetPaddockHorseIndex`
- `ChangeMode`
- `UpdateSilentTime`
- `GetNextModeByEmpty`
- `IsCommentEnable`
- `FirstExec`

</details>


### `Gallop.JikkyoTagProcessor` — score 5
<details><summary>Methods</summary>

- `GetTagIndex`
- `GetTagList`
- `MakeTag`
- `.ctor`
- `ReplaceTag`
- `ReplaceSoundTag`
- `ReplaceTagInner`
- `RegisterCalledOmitTag`
- `GetOmitTagGroup`
- `InitOmitTagTime`
- `InitOmitTag`
- `UpdateOmitTagCharaId`
- `UpdateCalledTagList`
- `UpdateSameCharaIdDict`
- `ExistSameCharaId`
- `SetTagBasin`
- `SetTagGoodStart`
- `SetTagBadStart`
- `UpdateTagHorseRank`
- `GetPopSound`
- `UpdateTagRace`
- `UpdateTagRaceName`
- `UpdateTagSingleModeTeamRace`
- `UpdateTagRaceHorseNum`
- `UpdateTagCourseName`
- `UpdateTagDistanceAndGroundType`
- `UpdateTagPlayerHorse`
- `UpdateTagPaddockHorse`
- `UpdateTagByHorse`
- `_SetTag`
- `_SetSoundTag`
- `IsContainsRank`
- `ConcatSoundTag`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 0 | TAG_COURSE | System.String |
| 0 | TAG_RACE | System.String |
| 0 | TAG_RACE_WO | System.String |
| 0 | TAG_DISTANCE | System.String |
| 0 | TAG_GROUND | System.String |
| 0 | TAG_HORSE_NUM | System.String |
| 0 | TAG_HORSE_NUM_NO | System.String |
| 0 | TAG_WAKU_BAN | System.String |
| 0 | TAG_BAN | System.String |
| 0 | TAG_BAN_NO | System.String |
| 0 | TAG_BAN_TO | System.String |
| 0 | TAG_BAN_TA | System.String |
| 0 | TAG_HORSE | System.String |
| 0 | TAG_HORSE_L | System.String |
| 0 | TAG_HORSE_NO | System.String |
| 0 | TAG_HORSE_TO | System.String |
| 0 | TAG_HORSE_TA | System.String |
| 0 | TAG_HORSE_A | System.String |
| 0 | TAG_A_HORSE | System.String |
| 0 | TAG_H_PLAYER | System.String |
| 0 | TAG_H_PLAYER_L | System.String |
| 0 | TAG_H_PLAYER_NO | System.String |
| 0 | TAG_H_PLAYER_TO | System.String |
| 0 | TAG_H_PLAYER_TA | System.String |
| 0 | TAG_H_PLAYER_A | System.String |
| 0 | TAG_A_H_PLAYER | System.String |
| 0 | TAG_P_WAKU_BAN | System.String |
| 0 | TAG_P_BAN | System.String |
| 0 | TAG_H_PADDOCK | System.String |
| 0 | TAG_H_PADDOCK_L | System.String |
| 0 | TAG_H_PADDOCK_NO | System.String |
| 0 | TAG_H_PADDOCK_TO | System.String |
| 0 | TAG_H_PADDOCK_TA | System.String |
| 0 | TAG_H_PADDOCK_A | System.String |
| 0 | TAG_H_RANK | System.String |
| 0 | TAG_H_RANK_L | System.String |
| 0 | TAG_H_RANK_NO | System.String |
| 0 | TAG_H_RANK_TO | System.String |
| 0 | TAG_H_RANK_TA | System.String |
| 0 | TAG_H_RANK_A | System.String |
| 0 | TAG_A_H_RANK | System.String |
| 0 | TAG_H_POP | System.String |
| 0 | TAG_H_POP_L | System.String |
| 0 | TAG_H_POP_NO | System.String |
| 0 | TAG_H_POP_TO | System.String |
| 0 | TAG_H_POP_TA | System.String |
| 0 | TAG_H_POP_A | System.String |
| 0 | TAG_A_H_POP | System.String |
| 0 | TAG_TEAM_NAME | System.String |
| 0 | TAG_TEAM_HONOR | System.String |
| 0 | TAG_POP | System.String |
| 0 | TAG_POP_NO | System.String |
| 0 | TAG_H_GOODS | System.String |
| 0 | TAG_H_GOODS_TA | System.String |
| 0 | TAG_H_BADS | System.String |
| 0 | TAG_BASIN | System.String |
| 0 | TAG_BASIN_L | System.String |
| 0 | TAG_L_BASIN | System.String |
| 0 | TAG_LEGEND_HORSE | System.String |
| 0 | TAG_WAIT | System.String |
| 0 | TAG_CROSS | System.String |
| 0 | BASIN_TAG_MAX | System.Int32 |
| 16 | NO_VOICE_CHARA_ID_ARRAY | System.Int32[] |
| 24 | _tagText | System.String[] |
| 32 | _tagSound | System.String[] |
| 40 | _horseTagKeys | Gallop.JikkyoTagProcessor.HorseTagKey[] |
| 48 | _horseTagValues | Gallop.JikkyoTagProcessor.HorseTagValue[] |
| 56 | _horseSoundTagValues | Gallop.JikkyoTagProcessor.HorseTagValue[] |
| 0 | DictionaryTempNum | System.Int32 |
| 64 | _sameCharaIdDict | System.Collections.Generic.Dictionary<System.Int32,System.Int32> |
| 72 | _basinTagValueDict | System.Collections.Generic.Dictionary<System.Int32,System.String> |
| 80 | _basinSoundTagValueDict | System.Collections.Generic.Dictionary<System.Int32,System.String> |
| 88 | _basinLTagValueDict | System.Collections.Generic.Dictionary<System.Int32,System.String> |
| 96 | _basinLSoundTagValueDict | System.Collections.Generic.Dictionary<System.Int32,System.String> |
| 104 | _lBasinTagValueDict | System.Collections.Generic.Dictionary<System.Int32,System.String> |
| 112 | _lBasinSoundTagValueDict | System.Collections.Generic.Dictionary<System.Int32,System.String> |
| 0 | TempolaryStringBuilderNum | System.Int32 |
| 120 | _stringBuilder | System.Text.StringBuilder |
| 128 | _globalTagIndex | Gallop.JikkyoTagProcessor.GlobalTagIndex |
| 136 | _courseSet | Gallop.MasterRaceCourseSet.RaceCourseSet |
| 144 | _raceId | System.Int32 |
| 152 | _raceName | System.String |
| 160 | _horseArray | Gallop.HorseData[] |
| 168 | _horseIndexByPopularity | System.Int32[] |
| 176 | _horseNum | System.Int32 |
| 184 | _getHorseIndexByOrder | System.Func<System.Int32,System.Int32> |
| 192 | _getPlayerHorseIndex | System.Func<System.Int32> |
| 200 | _omitTagTimeMax | System.Single |
| 0 | OMIT_TAG_GROUP_NULL | System.Int32 |
| 208 | _omitTagDic | System.Collections.Generic.Dictionary<System.Int32,System.Collections.Generic.List<Gallop.JikkyoTagProcessor.OmitTagInfo>> |
| 216 | _calledTagList | System.Collections.Generic.List<Gallop.JikkyoTagProcessor.CalledTag> |

</details>


### `Gallop.JikkyoTagProcessor.GlobalTagIndex` — score 5
<details><summary>Methods</summary>

- `Initialize`
- `.ctor`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 16 | tagCourse | System.Int32 |
| 20 | tagRace | System.Int32 |
| 24 | tagRaceWo | System.Int32 |
| 28 | tagDistance | System.Int32 |
| 32 | tagGround | System.Int32 |
| 36 | tagHorseNum | System.Int32 |
| 40 | tagHorseNumNo | System.Int32 |
| 44 | tagHPlayer | System.Int32 |
| 48 | tagHPlayerL | System.Int32 |
| 52 | tagHPlayerNo | System.Int32 |
| 56 | tagHPlayerTo | System.Int32 |
| 60 | tagHPlayerTa | System.Int32 |
| 64 | tagHPlayerA | System.Int32 |
| 68 | tagAHPlayer | System.Int32 |
| 72 | tagPWakuBan | System.Int32 |
| 76 | tagPBan | System.Int32 |
| 80 | TagHPaddock | System.Int32 |
| 84 | TagHPaddockL | System.Int32 |
| 88 | TagHPaddockNo | System.Int32 |
| 92 | TagHPaddockTo | System.Int32 |
| 96 | TagHPaddockTa | System.Int32 |
| 100 | TagHPaddockA | System.Int32 |
| 104 | tagRank | System.Int32[] |
| 112 | tagRankL | System.Int32[] |
| 120 | tagRankNo | System.Int32[] |
| 128 | tagRankTo | System.Int32[] |
| 136 | tagRankTa | System.Int32[] |
| 144 | tagRankA | System.Int32[] |
| 152 | tagARank | System.Int32[] |
| 160 | tagHPop | System.Int32[] |
| 168 | tagHPopL | System.Int32[] |
| 176 | tagHPopNo | System.Int32[] |
| 184 | tagHPopTo | System.Int32[] |
| 192 | tagHPopTa | System.Int32[] |
| 200 | tagHPopA | System.Int32[] |
| 208 | tagAHPop | System.Int32[] |
| 216 | tagPop | System.Int32[] |
| 224 | tagPopNo | System.Int32[] |
| 232 | tagHGood | System.Int32[] |
| 240 | tagHGoodTa | System.Int32[] |
| 248 | tagHBad | System.Int32[] |
| 256 | tagBasin | System.Int32 |
| 260 | TagBasinL | System.Int32 |
| 264 | TagLBasin | System.Int32 |
| 268 | tagLegend | System.Int32 |
| 272 | tagWait | System.Int32 |
| 276 | tagCross | System.Int32 |
| 280 | TagSingleModeTeamName | System.Int32 |
| 284 | TagSingleModeTeamHonor | System.Int32 |

</details>


### `Gallop.JikkyoTrigger` — score 5
<details><summary>Methods</summary>

- `.ctor`
- `Initialize`
- `Release`
- `Update`
- `GetHorse`
- `IsJikkyoTriggerOK`
- `_IsAfterCheckHorseType`
- `_CheckTrigger`
- `_GetCommandFunc`
- `_InitTriggerCmd`
- `Cmd_None`
- `Cmd_NoPlayer`
- `Cmd_Weather`
- `Cmd_Course`
- `Cmd_Race`
- `Cmd_Grade`
- `Cmd_Ground`
- `Cmd_GroundCondition`
- `Cmd_CourseDis`
- `Cmd_CourseAround`
- `Cmd_Popularity`
- `Cmd_Order`
- `Cmd_BackOrder`
- `Cmd_CharaID`
- `Cmd_ClothType`
- `Cmd_JikkyouMode`
- `Cmd_Lane`
- `Cmd_LaneDistance`
- `Cmd_LaneDiff`
- `Cmd_Length`
- `Cmd_RunStyle`
- `Cmd_GoodStart`
- `Cmd_BadStart`
- `Cmd_TopMember`
- `GetFirstHorseDistance`
- `Cmd_BagunLen`
- `Cmd_RankChange`
- `Cmd_TimeSpeedChange`
- `Cmd_TimeRankChange`
- `Cmd_Between`
- `Cmd_DistanceApproach`
- `Cmd_DistanceAway`
- `Cmd_FinalRank`
- `Cmd_RankHigher`
- `Cmd_Block`
- `Cmd_BlockMotion`
- `Cmd_NonTemptationTime`
- `Cmd_LastCorner`
- `Cmd_HPRate`
- `Cmd_TopGroupExist`
- `Cmd_Event_Distance`
- `Cmd_Event_Corner`
- `Cmd_Event_Param`
- `Cmd_RaceIdRange`
- `Cmd_LastSpurt`
- `Cmd_Skill`
- `Cmd_SkillReceived`
- `Cmd_SkillExtension`
- `Cmd_HorseNum`
- `Cmd_GroundChange`
- `Cmd_DistanceToLastCorner`
- `Cmd_SkillCutinPrev`
- `Cmd_Distance`
- `Cmd_NpcType`
- `Cmd_Temptation`
- `Cmd_LastBaseId`
- `Cmd_RelativeSpeed`
- `Cmd_OrderOneAfterAnother`
- `Cmd_InterruptOrderChange`
- `Cmd_FinishLength`
- `Cmd_ParamSpeedRank`
- `Cmd_ParamStaminaRank`
- `Cmd_ParamPowerRank`
- `Cmd_ParamGutsRank`
- `Cmd_ParamWizRank`
- `Cmd_PlayerTemptation`
- `Cmd_SkillActivate`
- `Cmd_StaminaZeroDistance`
- `Cmd_JikkyouActorId`
- `Cmd_CommentActorId`
- `Cmd_MainParamRank`
- `Cmd_StaminaZeroHorseNum`
- `Cmd_RelativeSpeedHorseNum`
- `Cmd_Positioning`
- `Cmd_CompareDistance`
- `Cmd_HomeStraight`
- `Cmd_BackStraight`
- `Cmd_WinnerStandFirstTime`
- `Cmd_UpdateCurHorse`
- `Cmd_Time`
- `Cmd_SingleModeDegreeType`
- `Cmd_WinSaddle`
- `Cmd_Undefeated`
- `Cmd_WinRace`
- `Cmd_NotWinRaceGroup1`
- `Cmd_RaceGroup`
- `Cmd_RaceType`
- `Cmd_TeamStadiumPromotionType`
- `Cmd_TeamStadiumCurrentRound`
- `Cmd_TeamStadiumRoundResult`
- `Cmd_TeamStadiumWinCount`
- `CountTeamStadiumWinCount`
- `Cmd_TeamStadiumScoreRecord`
- `Cmd_SingleModeTeamRaceCurrentRound`
- `Cmd_SingleModeTeamRaceRoundResult`
- `Cmd_SingleModeTeamRaceWinCount`
- `Cmd_SingleModeTeamRaceBossBattle`
- `Cmd_SingleModeTeamRaceHonor`
- `GetSingleModeTeamRaceBestFinishOrder`
- `CountSingleModeTeamRaceWinCount`
- `IsSingleModeScenarioFree`
- `GetTSCPlayerResult`
- `GetTSCPlayerWinPoint`
- `GetTSCPlayerTotalWinPoint`
- `GetTSCNPCResult`
- `GetTSCNPCTotalWinPoint`
- `InitSingleModeFree`
- `Cmd_SingleModeFreeRaceResult`
- `Cmd_SingleModeFreeTopPointDiff`
- `GetNPCHorse`
- `Cmd_SingleModeFreeTopAndSecondPointDiff`
- `Cmd_SingleModeFreeTotalPointRank`
- `Cmd_SingleModeScenarioId`
- `Cmd_SingleModePlayRaceInstanceId`
- `Cmd_PopularityMarkRank`
- `Cmd_PopularityMarkRankTopCount`
- `Cmd_Motivation`
- `Cmd_ProperGround`
- `Cmd_ProperDistance`
- `Cmd_ProperRunningStyle`
- `InitSingleModeRaceResultList`
- `InitSingleModeWinCountGIDic`
- `InitSingleModeWinCountGradeDic`
- `InitSingleModeEntryCountGradeDic`
- `InitSingleModeWinCount`
- `Cmd_SingleModeWinCountGI`
- `Cmd_SingleModeNotWinGIRaceCourse`
- `Cmd_CharaIdEntry`
- `Cmd_SingleModeWinCountGrade`
- `Cmd_SingleModeEntryCountGrade`
- `Cmd_SingleModeWinCount`
- `Cmd_GroundType`
- `_CheckHPRate`
- `_CheckTopGroupExist`
- `CheckSkill`
- `_GetLaneDiff`
- `_CheckTimeSpeedCheck`
- `_CheckTimeSpeedCheckMaxHorse`
- `_CheckTimeRankChange`
- `_HorseDistanceCheck`
- `CalcChangeDitance`
- `_CheckBlock`
- `_CheckRelativeSpeed`
- `_CheckTemptation`
- `_SetCurHorse`
- `SetPaddockHorse`
- `_GetHorse`
- `_CheckInequality`
- `_IsInequality`
- `_InitFrameData`
- `_UpdateFrameData`
- `_GetFrameData`
- `_GetFrameData_InterpolatedDistance`
- `_GetFrameData_InterpolatedSpeed`
- `UpdatePrevOrder`
- `_UpdateOrderCheckList`
- `_GetNextOrderHorseIndex`
- `OnStartInterruptOrder`
- `OnEndInterruptOrder`
- `SetCalledNextOrderHorse`
- `_InitParamRankPerList`
- `_CreateParamRankPercentageList`
- `_InitTemptationList`
- `_UpdateTemptation`
- `DecideLastCalledTemptationHorse`
- `_InitStaminaZeroRestDistanceList`
- `_InitWinnerStandFirstTime`
- `_SearchWinnerStandFirstTime`
- `_InitPositioningRange`
- `_IsPositioningSuccess`
- `_CheckStraight`
- `OnStartSituation`
- `.cctor`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 0 | HORSE_LANE_SIZE | System.Single |
| 0 | HORSE_LENGTH_DISTANCE_HALF | System.Single |
| 0 | FLOAT_SCALE | System.Single |
| 0 | PARAM_VALUE_SCALE | System.Int32 |
| 0 | BLOCK_FLAGS | Gallop.JikkyoTrigger.BlockFlags[] |
| 0 | SINGLE_MODE_FREE_RANK_NULL | System.Int32 |
| 16 | _jikkyo | Gallop.JikkyoControllerBase |
| 24 | _curHorseInfo | Gallop.IHorseRaceInfo |
| 32 | _paddockHorseInfo | Gallop.IHorseRaceInfo |
| 40 | _commandFuncDic | System.Collections.Generic.Dictionary<Gallop.JikkyoTrigger.Command,System.Func<Gallop.RaceJikkyoTriggerElementCache,System.Boolean>> |
| 48 | _curTimeSec | System.Int32 |
| 56 | _prevOrder | System.Int32[] |
| 64 | _frameDataList | Gallop.JikkyoTrigger.FrameData[] |
| 72 | _tmpHorseList | System.Collections.Generic.List<Gallop.IHorseRaceInfo> |
| 0 | AfterCheckTriggerSize | System.Int32 |
| 80 | _afterCheckTrigger | System.Collections.Generic.List<Gallop.RaceJikkyoTriggerElementCache> |
| 88 | _targetHorsesFinishRankTop3 | Gallop.IHorseRaceInfo[] |
| 96 | _nextOrderHorseIndex | System.Int32 |
| 104 | _nextOrderCheckList | System.Boolean[] |
| 112 | _interruptOrderHorseIndexList | System.Int32[] |
| 120 | _prevInterruptOrderHorseIndexList | System.Int32[] |
| 128 | _interruptOrderIndex | System.Int32 |
| 132 | _lastCalledHorseIndex | System.Int32 |
| 136 | _pickupHorseInfo | Gallop.IHorseRaceInfo |
| 144 | _paramSpeedRankPerList | System.Int32[] |
| 152 | _paramStaminaRankPerList | System.Int32[] |
| 160 | _paramPowerRankPerList | System.Int32[] |
| 168 | _paramGutsRankPerList | System.Int32[] |
| 176 | _paramWizRankPerList | System.Int32[] |
| 184 | _mainParamRankPerList | System.Int32[] |
| 192 | _temptationCountList | System.Int32[] |
| 200 | _isTemptationList | System.Boolean[] |
| 208 | _lastCheckedTemptationHorseIndex | System.Int32 |
| 212 | _lastCalledTemptationHorseIndex | System.Int32 |
| 216 | _staminaZeroRestDistanceList | System.Int32[] |
| 224 | _winnerStandFirstTime | System.Single |
| 232 | _positioningRange | System.Int32[][] |
| 240 | _winRaceGroup1RaceInstanceIdArray | System.Int32[] |
| 248 | _singleModeWinCountGIDic | System.Collections.Generic.Dictionary<System.Int32,System.Int32> |
| 256 | _singleModeWinCountGradeDic | System.Collections.Generic.Dictionary<Gallop.RaceDefine.Grade,System.Int32> |
| 264 | _singleModeEntryCountGradeDic | System.Collections.Generic.Dictionary<Gallop.RaceDefine.Grade,System.Int32> |
| 272 | _singleModeWinCount | System.Int32 |
| 280 | _singleModeRaceResultList | System.Collections.Generic.List<Gallop.JikkyoTrigger.SingleModeRaceResultDesc> |
| 288 | _singleModeFreePlayerRankArray | System.Int32[] |
| 296 | _singleModeFreeTotalWinPointArrayArray | Gallop.JikkyoTrigger.SingleModeFreePointInfo[][] |
| 304 | _singleModeFreeTotalWinPointDscArrayArray | Gallop.JikkyoTrigger.SingleModeFreePointInfo[][] |
| 312 | _raceInfo | Gallop.RaceInfo |
| 320 | _horseAccessor | Gallop.IRaceHorseAccessor |
| 328 | _timeAccessor | Gallop.IRaceTimeAccessor |
| 336 | _courseAttributeAccessor | Gallop.IRaceCourseAttributeAccessor |

</details>


### `Gallop.JikkyouTextController` — score 5
<details><summary>Methods</summary>

- `Init`
- `UpdateItems`
- `UpdateItemsImmidiate`
- `SetMessage`
- `SetUpItems`
- `GetDisplayIndex`
- `GetLastIndex`
- `MoveDisplayIndex`
- `.ctor`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 0 | MOVE_TIME | System.Single |
| 0 | OPAQUE_TEXT_INDEX_MAX | System.Int32 |
| 0 | DEFAULT_TEXT_ALPHA | System.Single |
| 0 | PAST_TEXT_ALPHA | System.Single |
| 32 | _itemHeight | System.Single |
| 36 | _baseAnchoredPosY | System.Single |
| 40 | _items | Gallop.JikkyouTextItem[] |
| 48 | _displayBaseIndex | System.Int32 |
| 52 | _itemNum | System.Int32 |
| 56 | _isInitialized | System.Boolean |
| 60 | _itemSize | UnityEngine.Vector2 |
| 0 | JIKKYO_TEXT_WIDTH_LANDSCAPE | System.Single |

</details>


### `Gallop.JikkyouTextItem` — score 5
<details><summary>Methods</summary>

- `get_IsSpeaking`
- `set_IsSpeaking`
- `get_Message`
- `Init`
- `SetMessage`
- `SetAnchoredPosY`
- `SetAnchoredPosYImmidiate`
- `SetTextAlpha`
- `SetVisible`
- `SetVisibleJikkyo`
- `SetVisibleComment`
- `SetVisibleMessage`
- `SetVisibleSeparator`
- `CreateCanvasGroup`
- `.ctor`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 32 | _jikkyouObj | UnityEngine.GameObject |
| 40 | _commentObj | UnityEngine.GameObject |
| 48 | _message | Gallop.TextCommon |
| 56 | _separator | UnityEngine.GameObject |
| 64 | _itemCanvasGroup | UnityEngine.CanvasGroup |
| 72 | _jikkyoCanvasGroup | UnityEngine.CanvasGroup |
| 80 | _commentCanvasGroup | UnityEngine.CanvasGroup |
| 88 | _messageCanvasGroup | UnityEngine.CanvasGroup |
| 96 | _separatorCanvasGroup | UnityEngine.CanvasGroup |
| 104 | _rectTransform | UnityEngine.RectTransform |
| 112 | _isVisibleJikkyo | System.Boolean |
| 113 | _isVisibleComment | System.Boolean |
| 114 | _isVisibleMessage | System.Boolean |
| 116 | _textAlpha | System.Single |
| 120 | <IsSpeaking>k__BackingField | System.Boolean |

</details>


### `Gallop.JikkyouVoiceLoader` — score 5
<details><summary>Methods</summary>

- `Load`
- `Release`
- `IsLoading`
- `GetDownloadCueSheetNameList`
- `RegisterCueSheetDictionary`
- `RegisterSingleCueSheet`
- `GetCueSheets`
- `GetCueSheetNameHorse`
- `GetCueSheetNameCommon`
- `ExistCueSheetNameCommon`
- `_GetCueSheetNameSingle`
- `GetCueSheetNameWakuBan`
- `GetCueSheetNameBan`
- `GetCueSheetNamePop`
- `GetCueSheetNameBasin`
- `GetCueSheetNameHorseNum`
- `GetCueSheetNameCategory`
- `GetCueSheetNameCourse`
- `GetCueSheetNameRace`
- `_GetCueSheetNamesRace`
- `GetRaceNameCueSheetInfo`
- `GetRaceNameCueSheetInfoInternal`
- `SetupActorId`
- `IsSingleModeScenarioFree`
- `GetActorId`
- `.ctor`
- `.cctor`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 0 | CUESHEET_FMT_ACTORID | System.String |
| 0 | CUESHEET_PREFIX_JKY | System.String |
| 0 | CUESHEET_PREFIX_CMT | System.String |
| 0 | CUESHEET_FMT_COMMON | System.String[] |
| 8 | CUESHEET_FMT_WAKU_BAN | System.String[] |
| 16 | CUESHEET_FMT_BAN | System.String[] |
| 24 | CUESHEET_FMT_POP | System.String[] |
| 32 | CUESHEET_FMT_BASIN | System.String[] |
| 40 | CUESHEET_FMT_NUM | System.String[] |
| 48 | CUESHEET_FMT_CATEGORY | System.String[] |
| 56 | CUESHEET_FMT_HORSENAME | System.String[] |
| 64 | CUESHEET_FMT_COURSE | System.String[] |
| 72 | CUESHEET_FMT_RACE | System.String[] |
| 0 | ORDINARY_ACTOR_ID_JKY_M | System.Int32 |
| 0 | ORDINARY_ACTOR_ID_JKY_F | System.Int32 |
| 0 | ORDINARY_ACTOR_ID_CMT | System.Int32 |
| 0 | SINGLE_MODE_FREE_ACTOR_ID_CMT | System.Int32 |
| 0 | UNKNOWN_ACTOR_ID | System.Int32 |
| 80 | _loadedCueSheets | System.Collections.Generic.List<System.String> |
| 88 | _cueSheetSingle | System.Collections.Generic.Dictionary<System.Int32,System.String[]> |
| 96 | _cueSheetHorseName | System.Collections.Generic.Dictionary<System.Int32,System.String[]> |
| 104 | _cueSheetRace | System.Collections.Generic.Dictionary<System.Int32,System.String> |
| 112 | _cueSheetRaceHorse | System.Collections.Generic.Dictionary<System.Int32,System.String[]> |
| 120 | _cueIdCueSheetDict | System.Collections.Generic.List<System.Collections.Generic.Dictionary<System.Int32,System.String>> |
| 128 | _actorIdJikkyou | System.Int32 |
| 132 | _actorIdComment | System.Int32 |

</details>


### `Gallop.JikkyoVoice` — score 5
<details><summary>Methods</summary>

- `Init`
- `Clear`
- `Cancel`
- `Pause`
- `Update`
- `IsCrossCommand`
- `PlayVoiceSequential`
- `PlayCommand`
- `IsEnd`
- `GetLength`
- `GetPlayTime`
- `IsCmdError`
- `GetCmdErrorMessage`
- `SetCmdErrorMessage`
- `ClearCmdError`
- `GetCommands`
- `CreateCommand`
- `GetHorseNameCueId`
- `GetWakuBanCueId`
- `GetBanCueId`
- `GetBanTypeFromCueId`
- `GetPopCueId`
- `GetBasinCueId`
- `GetBasinLCueId`
- `GetLBasinCueId`
- `GetCourseCueId`
- `GetRaceCueId`
- `ConvertRaceCueIdToRaceWoCueId`
- `GetGroundTypeCueID`
- `GetDistanceCueID`
- `GetHorseNumCueId`
- `GetTeamNameCueId`
- `GetTeamHonorCueId`
- `InitCreateCommandFunc`
- `CreateHorseNameCmd_Default`
- `CreateHorseNameCmd_Long`
- `CreateHorseNameCmd_No`
- `CreateHorseNameCmd_To`
- `CreateHorseNameCmd_Ta`
- `CreateHorseNameCmd_A`
- `CreateHorseNameCmd_AAfter`
- `CreateHorseNameCmdInner`
- `CreateSingleModeTeamNameCmd`
- `CreateSingleModeTeamHonorCmd`
- `CreateCourseCmd`
- `CreateRaceCmd`
- `CreateWakuBanCmd`
- `CreateBanCmd`
- `CreatePopCmd`
- `CreateBasinCmd`
- `CreateBasinNoTensionCmd`
- `CreateBasinCmdCommon`
- `CreateHorseNumCmd`
- `CreateCategoryCmd`
- `CreateJikkyouCmd`
- `CreateWaitCmd`
- `IsUseAfterHorseNameCorssTime`
- `SetHorseNameCrossTime`
- `SetHorseNameWithPostpositionalCrossTime`
- `SetBanCrossTime`
- `SetBasinCrossTime`
- `GetInt`
- `CreateCommandInner`
- `SplitVoiceCommand`
- `.ctor`

</details>

<details><summary>Fields</summary>

| Offset | Name | Type |
|-------:|------|------|
| 0 | VOICE_COMMAND_SEPARATOR | System.Char |
| 0 | CMD_PREFIX_HORSENAME | System.String |
| 0 | CMD_PREFIX_HORSENAME_L | System.String |
| 0 | CMD_PREFIX_HORSENAME_NO | System.String |
| 0 | CMD_PREFIX_HORSENAME_TO | System.String |
| 0 | CMD_PREFIX_HORSENAME_TA | System.String |
| 0 | CMD_PREFIX_HORSENAME_A | System.String |
| 0 | CMD_PREFIX_A_HORSENAME | System.String |
| 0 | CMD_PREFIX_COURCENAME | System.String |
| 0 | CMD_PREFIX_RACENAME | System.String |
| 0 | CMD_PREFIX_WAKU_BAN | System.String |
| 0 | CMD_PREFIX_BAN | System.String |
| 0 | CMD_PREFIX_POP | System.String |
| 0 | CMD_PREFIX_BASIN | System.String |
| 0 | CMD_PREFIX_BASIN_NO_TENSION | System.String |
| 0 | CMD_PREFIX_HORSE_NUM | System.String |
| 0 | CMD_PREFIX_CATEGORY | System.String |
| 0 | CMD_PREFIX_SINGLE_MODE_TEAM_NAME | System.String |
| 0 | CMD_PREFIX_SINGLE_MODE_TEAM_HONOR | System.String |
| 0 | CMD_PREFIX_WAIT | System.String |
| 0 | CMD_PREFIX_CROSS | System.String |
| 0 | RACE_ID_DIGIT | System.Int32 |
| 16 | _cmds | System.Collections.Generic.List<Gallop.IVoiceCmd> |
| 24 | _cmdPlayingIndex | System.Int32 |
| 28 | _isEnd | System.Boolean |
| 29 | _isCmdError | System.Boolean |
| 32 | _cmdErrorMessage | System.String |
| 40 | _beforeHorseNameCrossTimeArray | System.Single[] |
| 48 | _beforeHorseNameBanCrossTimeArray | System.Single[] |
| 56 | _afterHorseNameCrossTimeArray | System.Single[] |
| 64 | _beforeHorseNameWithPostpositionalCrossTimeArray | System.Single[] |
| 72 | _createCmdFuncDictionary | System.Collections.Generic.Dictionary<System.String,Gallop.JikkyoVoice.CreateCmdFunc> |

</details>


### `Gallop.JikkyoVoice.CreateCmdFunc` — score 5
<details><summary>Methods</summary>

- `.ctor`
- `Invoke`
- `BeginInvoke`
- `EndInvoke`

</details>

