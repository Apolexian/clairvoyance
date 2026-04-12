// hook_skills.js
// Hooks skill activation, lottery, and related methods.
// Loaded after il2cpp_helpers.js inside a collector IIFE.

(function () {
    "use strict";

    console.log("[skills] Scanning for skill classes...");

    const SKILL_CLASSES = [
        "Gallop.SkillBase",
        "Gallop.SkillDetail",
        "Gallop.SkillManager",
        "Gallop.SkillAbility",
        "Gallop.SkillAbilityCreator",
    ];

    const classLookup = {};
    const classInfos = {};

    iterAssemblyClasses(function (classPtr, fullName, ns, name) {
        if (SKILL_CLASSES.indexOf(fullName) !== -1) {
            console.log("[skills] Found: " + fullName);
            classInfos[fullName] = extractClassInfo(classPtr, fullName);
        }
    });

    let hookCount = 0;

    // ── SkillDetail.Activate ──────────────────────────────────────────
    // Fires when a skill actually activates during a race.
    const detail = classInfos["Gallop.SkillDetail"];
    if (detail) {
        if (
            hookMethod(detail, "Activate", -1, {
                onEnter: function (args) {
                    const self = args[0];
                    const record = { event: "skill_activate" };

                    // Read ALL fields from SkillDetail using readObjectFields
                    const fields = readObjectFields(self, detail.fieldList);
                    if (fields) {
                        for (const k in fields) {
                            record[k] = fields[k];
                        }
                    }

                    // Also try legacy specific field names as fallback
                    if (!record.SkillId && !record.skillId && !record._skillId) {
                        for (const f of detail.fieldList) {
                            if (
                                f.name === "SkillId" ||
                                f.name === "skillId" ||
                                f.name === "_skillId"
                            ) {
                                try {
                                    record.skillId = self.add(f.offset).readS32();
                                } catch (e) {}
                            }
                            if (f.name === "Level" || f.name === "level" || f.name === "_level") {
                                try {
                                    record.level = self.add(f.offset).readS32();
                                } catch (e) {}
                            }
                        }
                    }

                    send({ type: "collect", domain: "skills", data: record });
                    // Also cross-send to race domain for race analysis correlation
                    send({
                        type: "collect",
                        domain: "race",
                        data: {
                            event: "race_skill_activate",
                            class: "Gallop.SkillDetail.Activate",
                            source: "skills_module",
                            ...record,
                        },
                    });
                },
            })
        )
            hookCount++;

        // RecordSkillEvent — sometimes has more detail
        if (
            hookMethod(detail, "RecordSkillEvent", -1, {
                onEnter: function (args) {
                    send({
                        type: "collect",
                        domain: "skills",
                        data: { event: "record_skill_event" },
                    });
                },
            })
        )
            hookCount++;
    }

    // ── SkillBase.LotActivate ─────────────────────────────────────────
    // This is the proc chance lottery — fires when the game rolls whether
    // a skill will proc.
    const base = classInfos["Gallop.SkillBase"];
    if (base) {
        if (
            hookMethod(base, "LotActivate", -1, {
                onEnter: function (args) {
                    send({
                        type: "collect",
                        domain: "skills",
                        data: { event: "lot_activate_enter" },
                    });
                },
                onLeave: function (retval) {
                    const result = retval.toInt32();
                    send({
                        type: "collect",
                        domain: "skills",
                        data: {
                            event: "lot_activate_result",
                            procced: result !== 0,
                            rawResult: result,
                        },
                    });
                },
            })
        )
            hookCount++;

        // CheckTriggerAndActivate — the full trigger check + activation pipeline
        if (
            hookMethod(base, "CheckTriggerAndActivate", -1, {
                onEnter: function (args) {
                    send({
                        type: "collect",
                        domain: "skills",
                        data: { event: "check_trigger_enter" },
                    });
                },
                onLeave: function (retval) {
                    send({
                        type: "collect",
                        domain: "skills",
                        data: {
                            event: "check_trigger_result",
                            activated: retval.toInt32() !== 0,
                        },
                    });
                },
            })
        )
            hookCount++;
    }

    // ── SkillManager ──────────────────────────────────────────────────
    const mgr = classInfos["Gallop.SkillManager"];
    if (mgr) {
        // UpdateSkill — called per-tick, too noisy to log args but
        // we can count for frequency analysis
        // (skip — too hot)

        // ActivateSkill — when manager decides to fire a skill
        if (
            hookMethod(mgr, "ActivateSkill", -1, {
                onEnter: function (args) {
                    const record = { event: "manager_activate_skill" };

                    // Try reading args[1] as a skill ID (int)
                    if (args.length > 1) {
                        try {
                            const asInt = args[1].toInt32();
                            if (asInt >= 100000 && asInt <= 999999) {
                                record.skill_id = asInt;
                            } else if (asInt > 0) {
                                record.arg1_int = asInt;
                            }
                        } catch (e) {}
                    }
                    // Try reading args[2] as horse index
                    if (args.length > 2) {
                        try {
                            const arg2 = args[2].toInt32();
                            if (arg2 >= 0 && arg2 < 18) {
                                record.horse_index = arg2;
                            }
                        } catch (e) {}
                    }

                    send({
                        type: "collect",
                        domain: "skills",
                        data: record,
                    });
                },
            })
        )
            hookCount++;
    }

    console.log("[skills] " + hookCount + " hooks installed.");
    send({ type: "hook_status", module: "skills", hookCount: hookCount });
})();
