// hook_races.js
// Hooks race lifecycle, simulation data, skill activations, and per-frame state.
// Loaded after il2cpp_helpers.js inside a collector IIFE.
//
// KEY DATA SOURCES (from hakuraku analysis):
// 1. RaceManager / RaceModelController — holds the race simulation binary
// 2. RaceSimulateData — the binary blob with frames, results, events
// 3. Skill activation events (SKILL type = 3 in the event data)
// 4. HorseTemptationCalculator — pace/temptation mode changes
// 5. Race horse frame data — per-tick distance, speed, HP, lane position

(function () {
    "use strict";

    console.log("[races] Scanning for race classes...");

    // ── Phase 1: Find all race-related classes ─────────────────────────

    var RACE_KEYWORDS = [
        "racemanager",
        "raceresult",
        "racecamera",
        "racehorsedata",
        "racedefine",
        "jikkyomanager",
        "jikkyocomment",
        "racemodelcontroller",
        "raceplayer",
        "racesimulate",
        "racehorsecontroller",
        "horseskill",
        "skillmanager",
        "temptation",
        "racehorseparam",
        "racesequence",
        "raceinfo",
        "racedatamanager",
    ];

    var classInfos = {};
    var raceClassPtrs = {};

    iterAssemblyClasses(function (classPtr, fullName, ns, name) {
        var lower = fullName.toLowerCase();
        if (
            RACE_KEYWORDS.some(function (kw) {
                return lower.includes(kw);
            })
        ) {
            console.log("[races] Found: " + fullName);
            classInfos[fullName] = extractClassInfo(classPtr, fullName);
            raceClassPtrs[fullName] = classPtr;
        }
    });

    var hookCount = 0;

    // ── Phase 2: Race lifecycle hooks ──────────────────────────────────
    // These tell us when a race starts, ends, and results are shown.

    var lifecycleMethods = [
        "BeginRace",
        "StartRace",
        "EndRace",
        "FinishRace",
        "BeginView",
        "Begin",
        "Start",
        "SetResult",
        "ShowResult",
        "OnFinish",
    ];

    for (var className in classInfos) {
        var classInfo = classInfos[className];

        for (var mi = 0; mi < lifecycleMethods.length; mi++) {
            var mName = lifecycleMethods[mi];
            if (!classInfo.methods[mName]) continue;

            var captured = className + "." + mName;
            if (
                hookMethod(classInfo, mName, -1, {
                    onEnter: (function (capturedName, cInfo) {
                        return function (args) {
                            var record = {
                                event: "race_lifecycle",
                                class: capturedName,
                            };

                            // Try to read fields from self
                            var self = args[0];
                            for (var fi = 0; fi < cInfo.fieldList.length; fi++) {
                                var f = cInfo.fieldList[fi];
                                var lower = f.name.toLowerCase();
                                // Read IDs and counters
                                if (
                                    (lower.includes("id") ||
                                        lower.includes("order") ||
                                        lower.includes("result") ||
                                        lower.includes("time") ||
                                        lower.includes("distance") ||
                                        lower.includes("weather") ||
                                        lower.includes("ground") ||
                                        lower.includes("grade") ||
                                        lower.includes("horse") ||
                                        lower.includes("course") ||
                                        lower.includes("length") ||
                                        lower.includes("condition")) &&
                                    (f.type.includes("Int32") || f.type.includes("Single"))
                                ) {
                                    try {
                                        if (f.type.includes("Single")) {
                                            record["field_" + f.name] = self
                                                .add(f.offset)
                                                .readFloat();
                                        } else {
                                            record["field_" + f.name] = self
                                                .add(f.offset)
                                                .readS32();
                                        }
                                    } catch (e) {}
                                }
                                // Read string fields
                                if (f.type === "System.String" || f.type === "string") {
                                    try {
                                        var strPtr = self.add(f.offset).readPointer();
                                        var str = readIl2cppString(strPtr);
                                        if (str) record["field_" + f.name] = str;
                                    } catch (e) {}
                                }
                            }

                            send({ type: "collect", domain: "race", data: record });
                        };
                    })(captured, classInfo),
                })
            )
                hookCount++;
        }
    }

    // ── Phase 3: Skill activation hooks ───────────────────────────────
    // Hook skill activation methods and extract actual skill IDs.
    //
    // Strategy:
    //  a) Hook SkillDetail.Activate — the canonical "skill fires" event.
    //     The `self` (args[0]) IS the SkillDetail with SkillId, Level, etc.
    //  b) Hook SkillManager.AddSkill — args[1] is the skill object being
    //     added; traverse its fields for the actual skill ID.
    //  c) For other skill classes, read args[1] as potential skill objects.

    // Helper: try to read a skill ID from an object pointer by scanning
    // known field names that typically hold the skill id.
    function tryReadSkillId(objPtr) {
        if (!objPtr || objPtr.isNull()) return null;
        // Common IL2CPP object layout: fields start at offset 0x10 (64-bit)
        // or 0x08 (32-bit) after klass + monitor. For Int32 fields that
        // are "Id"-like, try small offsets typical for SkillDetail.
        var result = {};
        try {
            // Read a bunch of int32 fields at typical offsets (0x10..0x40)
            // and look for plausible skill IDs (6-digit numbers like 200xxx, 900xxx)
            var baseOff = ptrSize === 8 ? 0x10 : 0x08;
            for (var off = baseOff; off < baseOff + 0x40; off += 4) {
                try {
                    var val = objPtr.add(off).readS32();
                    // Skill IDs in Uma are typically 100000-999999 range
                    if (val >= 100000 && val <= 999999) {
                        result["int32_at_0x" + off.toString(16)] = val;
                    }
                    // Also capture small positive ints (level, rarity, etc.)
                    if (val > 0 && val <= 10 && !result.possibleLevel) {
                        result["small_int_at_0x" + off.toString(16)] = val;
                    }
                } catch (e) {}
            }
        } catch (e) {}
        return Object.keys(result).length > 0 ? result : null;
    }

    // ── 3a: SkillDetail.Activate — the best source ─────────────────
    // Find SkillDetail specifically and hook Activate with full field read
    var skillDetailInfo = null;
    for (var sdn in classInfos) {
        if (sdn.indexOf("SkillDetail") !== -1) {
            skillDetailInfo = classInfos[sdn];
            break;
        }
    }
    if (skillDetailInfo) {
        // Use extractClassInfoWithParents to also get inherited fields
        if (
            hookMethod(skillDetailInfo, "Activate", -1, {
                onEnter: (function (cInfo) {
                    return function (args) {
                        var self = args[0];
                        var record = {
                            event: "race_skill_activate",
                            class: cInfo.fullName + ".Activate",
                            source: "SkillDetail",
                        };

                        // Read ALL readable fields from the SkillDetail object
                        var fields = readObjectFields(self, cInfo.fieldList);
                        if (fields) {
                            for (var k in fields) {
                                record["field_" + k] = fields[k];
                            }
                        }

                        send({ type: "collect", domain: "race", data: record });
                        // Also send to skills domain for that log
                        send({ type: "collect", domain: "skills", data: record });
                    };
                })(skillDetailInfo),
            })
        )
            hookCount++;
    }

    // ── 3b: SkillManager methods — read the argument skill object ───
    var SKILL_MANAGER_METHODS = ["ActivateSkill", "AddSkill", "FireSkill", "UseSkill"];

    for (var cn in classInfos) {
        var ci = classInfos[cn];
        var cnLower = cn.toLowerCase();
        if (!cnLower.includes("skillmanager")) continue;

        for (var si = 0; si < SKILL_MANAGER_METHODS.length; si++) {
            var skillMeth = SKILL_MANAGER_METHODS[si];
            if (!ci.methods[skillMeth]) continue;

            var capturedSkill = cn + "." + skillMeth;
            if (
                hookMethod(ci, skillMeth, -1, {
                    onEnter: (function (capturedName, cInfo) {
                        return function (args) {
                            var record = {
                                event: "race_skill_activate",
                                class: capturedName,
                                source: "SkillManager",
                            };

                            // args[0] = this (SkillManager)
                            // args[1] = first method argument (likely skill object or skill id)
                            // Try reading args[1] as an object with fields
                            if (args.length > 1) {
                                try {
                                    var arg1 = args[1];
                                    // First, try as a plain int32 (skill ID directly)
                                    try {
                                        var asInt = arg1.toInt32();
                                        if (asInt >= 100000 && asInt <= 999999) {
                                            record.skill_id = asInt;
                                        } else if (asInt > 0) {
                                            record.arg1_int = asInt;
                                        }
                                    } catch (e) {}

                                    // Also try as an object pointer — scan for skill ID fields
                                    if (!record.skill_id) {
                                        var probed = tryReadSkillId(arg1);
                                        if (probed) {
                                            for (var pk in probed) {
                                                record["arg1_" + pk] = probed[pk];
                                            }
                                        }
                                    }
                                } catch (e) {}
                            }

                            // Also try reading args[2] (could be horse index)
                            if (args.length > 2) {
                                try {
                                    var arg2 = args[2].toInt32();
                                    if (arg2 >= 0 && arg2 < 18) {
                                        record.horse_index = arg2;
                                    } else if (arg2 >= 100000 && arg2 <= 999999) {
                                        record.skill_id_arg2 = arg2;
                                    }
                                } catch (e) {}
                            }

                            send({ type: "collect", domain: "race", data: record });
                        };
                    })(capturedSkill, ci),
                })
            )
                hookCount++;
        }
    }

    // ── 3c: Other skill-related classes (HorseSkill, etc.) ──────────
    var OTHER_SKILL_METHODS = ["OnSkillActivate", "TriggerSkill", "OnActivate"];

    for (var cn2 in classInfos) {
        var ci2 = classInfos[cn2];
        var cn2Lower = cn2.toLowerCase();
        // Skip classes already hooked above
        if (cn2Lower.includes("skillmanager") || cn2.indexOf("SkillDetail") !== -1) continue;
        if (!cn2Lower.includes("skill")) continue;

        for (var si2 = 0; si2 < OTHER_SKILL_METHODS.length; si2++) {
            var skillMeth2 = OTHER_SKILL_METHODS[si2];
            if (!ci2.methods[skillMeth2]) continue;

            var capturedSkill2 = cn2 + "." + skillMeth2;
            if (
                hookMethod(ci2, skillMeth2, -1, {
                    onEnter: (function (capturedName, cInfo) {
                        return function (args) {
                            var record = {
                                event: "race_skill_activate",
                                class: capturedName,
                                source: "other",
                            };

                            // Read all fields from self
                            var fields = readObjectFields(args[0], cInfo.fieldList);
                            if (fields) {
                                for (var k in fields) {
                                    record["field_" + k] = fields[k];
                                }
                            }

                            // Try args[1] as skill id or skill object
                            if (args.length > 1) {
                                try {
                                    var asInt = args[1].toInt32();
                                    if (asInt >= 100000 && asInt <= 999999) {
                                        record.skill_id = asInt;
                                    }
                                } catch (e) {}
                                var probed = tryReadSkillId(args[1]);
                                if (probed) {
                                    for (var pk2 in probed) {
                                        record["arg1_" + pk2] = probed[pk2];
                                    }
                                }
                            }

                            send({ type: "collect", domain: "race", data: record });
                        };
                    })(capturedSkill2, ci2),
                })
            )
                hookCount++;
        }
    }

    // ── Phase 4: Temptation / Pace mode hooks ─────────────────────────
    // HorseTemptationCalculator handles pace down / rush modes

    var TEMPTATION_METHODS = [
        "UpdateTemptation",
        "_UpdateTemptation",
        "SetTemptationMode",
        "StartTemptation",
        "EndTemptation",
        "OnTemptation",
        "CalcTemptation",
        "CheckTemptation",
        "SetMode",
    ];

    for (var tcn in classInfos) {
        var tci = classInfos[tcn];
        var tcnLower = tcn.toLowerCase();
        if (!tcnLower.includes("temptation") && !tcnLower.includes("pacedown")) continue;

        for (var ti = 0; ti < TEMPTATION_METHODS.length; ti++) {
            var tempMeth = TEMPTATION_METHODS[ti];
            if (!tci.methods[tempMeth]) continue;

            var capturedTemp = tcn + "." + tempMeth;
            if (
                hookMethod(tci, tempMeth, -1, {
                    onEnter: (function (capturedName, cInfo) {
                        return function (args) {
                            var record = {
                                event: "race_temptation",
                                class: capturedName,
                            };

                            var self = args[0];
                            for (var fi = 0; fi < cInfo.fieldList.length; fi++) {
                                var f = cInfo.fieldList[fi];
                                var lower = f.name.toLowerCase();
                                if (
                                    (lower.includes("mode") ||
                                        lower.includes("horse") ||
                                        lower.includes("index") ||
                                        lower.includes("tempt") ||
                                        lower.includes("time") ||
                                        lower.includes("speed") ||
                                        lower.includes("pace")) &&
                                    (f.type.includes("Int32") ||
                                        f.type.includes("Single") ||
                                        f.type.includes("Byte") ||
                                        f.type.includes("SByte"))
                                ) {
                                    try {
                                        if (f.type.includes("Single")) {
                                            record["field_" + f.name] = self
                                                .add(f.offset)
                                                .readFloat();
                                        } else if (
                                            f.type.includes("Byte") ||
                                            f.type.includes("SByte")
                                        ) {
                                            record["field_" + f.name] = self.add(f.offset).readS8();
                                        } else {
                                            record["field_" + f.name] = self
                                                .add(f.offset)
                                                .readS32();
                                        }
                                    } catch (e) {}
                                }
                            }

                            send({ type: "collect", domain: "race", data: record });
                        };
                    })(capturedTemp, tci),
                })
            )
                hookCount++;
        }
    }

    // ── Phase 5: Frame data sampling ──────────────────────────────────
    // Hook the race update loop to sample frame data periodically.
    // This gives us live per-horse state (distance, speed, HP, position).
    // We throttle to ~1 sample per second to avoid flooding.

    var UPDATE_METHODS = [
        "UpdateFrame",
        "_UpdateFrame",
        "UpdateFrameData",
        "_UpdateFrameData",
        "UpdateRace",
        "RaceUpdate",
        "FixedUpdate",
    ];

    var lastFrameSendTime = 0;
    var FRAME_SEND_INTERVAL = 1.0; // seconds between frame data sends

    for (var ucn in classInfos) {
        var uci = classInfos[ucn];
        var ucnLower = ucn.toLowerCase();
        // Only hook frame updates on actual race manager classes
        if (!ucnLower.includes("racemanager") && !ucnLower.includes("racemodelcontroller"))
            continue;

        for (var ui = 0; ui < UPDATE_METHODS.length; ui++) {
            var updateMeth = UPDATE_METHODS[ui];
            if (!uci.methods[updateMeth]) continue;

            var capturedUpdate = ucn + "." + updateMeth;
            if (
                hookMethod(uci, updateMeth, -1, {
                    onEnter: (function (capturedName, cInfo) {
                        return function (args) {
                            // Throttle: only send every FRAME_SEND_INTERVAL seconds
                            var now = Date.now() / 1000.0;
                            if (now - lastFrameSendTime < FRAME_SEND_INTERVAL) return;
                            lastFrameSendTime = now;

                            var record = {
                                event: "race_frame_sample",
                                class: capturedName,
                            };

                            // Read time-related and distance fields from self
                            var self = args[0];
                            for (var fi = 0; fi < cInfo.fieldList.length; fi++) {
                                var f = cInfo.fieldList[fi];
                                var lower = f.name.toLowerCase();
                                if (
                                    (lower.includes("time") ||
                                        lower.includes("frame") ||
                                        lower.includes("horse") ||
                                        lower.includes("count")) &&
                                    (f.type.includes("Int32") || f.type.includes("Single"))
                                ) {
                                    try {
                                        if (f.type.includes("Single")) {
                                            record["field_" + f.name] = self
                                                .add(f.offset)
                                                .readFloat();
                                        } else {
                                            record["field_" + f.name] = self
                                                .add(f.offset)
                                                .readS32();
                                        }
                                    } catch (e) {}
                                }
                            }

                            send({ type: "collect", domain: "race", data: record });
                        };
                    })(capturedUpdate, uci),
                })
            )
                hookCount++;
        }
    }

    // ── Phase 6: Jikkyo (commentary) hooks ────────────────────────────
    // Commentary triggers tell us what the game thinks is happening
    // (e.g. "Surging ahead!", "Falling behind!", "Last spurt!")

    var jikkyoMethods = ["PlayComment", "TriggerComment", "OnComment", "AddComment", "ShowComment"];

    for (var jcn in classInfos) {
        var jci = classInfos[jcn];
        var jcnLower = jcn.toLowerCase();
        if (!jcnLower.includes("jikkyo") && !jcnLower.includes("comment")) continue;

        for (var ji = 0; ji < jikkyoMethods.length; ji++) {
            var jMeth = jikkyoMethods[ji];
            if (!jci.methods[jMeth]) continue;

            var capturedJ = jcn + "." + jMeth;
            if (
                hookMethod(jci, jMeth, -1, {
                    onEnter: (function (capturedName, cInfo) {
                        return function (args) {
                            var record = {
                                event: "jikkyo_comment",
                                class: capturedName,
                            };

                            // Try to read comment ID or type from args
                            var self = args[0];
                            for (var fi = 0; fi < cInfo.fieldList.length; fi++) {
                                var f = cInfo.fieldList[fi];
                                var lower = f.name.toLowerCase();
                                if (
                                    (lower.includes("comment") ||
                                        lower.includes("id") ||
                                        lower.includes("type") ||
                                        lower.includes("horse") ||
                                        lower.includes("voice")) &&
                                    (f.type.includes("Int32") || f.type.includes("String"))
                                ) {
                                    try {
                                        if (f.type === "System.String" || f.type === "string") {
                                            var strPtr = self.add(f.offset).readPointer();
                                            var str = readIl2cppString(strPtr);
                                            if (str) record["field_" + f.name] = str;
                                        } else {
                                            record["field_" + f.name] = self
                                                .add(f.offset)
                                                .readS32();
                                        }
                                    } catch (e) {}
                                }
                            }

                            send({ type: "collect", domain: "race", data: record });
                        };
                    })(capturedJ, jci),
                })
            )
                hookCount++;
        }
    }

    // ── Summary ───────────────────────────────────────────────────────

    console.log("[races] " + hookCount + " hooks installed.");
    console.log("[races] Classes found: " + Object.keys(classInfos).join(", "));
    send({ type: "hook_status", module: "races", hookCount: hookCount });
})();
