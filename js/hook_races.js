// hook_races.js
// Hooks race lifecycle: start, finish, results.
// Loaded after il2cpp_helpers.js inside a collector IIFE.

(function () {
    "use strict";

    console.log("[races] Scanning for race classes...");

    const RACE_KEYWORDS = [
        "racemanager",
        "raceresult",
        "racecamera",
        "racehorsedata",
        "racedefine",
        "jikkyomanager",
        "jikkyocomment",
    ];

    const classInfos = {};

    iterAssemblyClasses(function (classPtr, fullName, ns, name) {
        const lower = fullName.toLowerCase();
        if (
            RACE_KEYWORDS.some(function (kw) {
                return lower.includes(kw);
            })
        ) {
            console.log("[races] Found: " + fullName);
            classInfos[fullName] = extractClassInfo(classPtr, fullName);
        }
    });

    let hookCount = 0;

    for (const [className, classInfo] of Object.entries(classInfos)) {
        // Race lifecycle methods
        const lifecycleMethods = [
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

        for (const mName of lifecycleMethods) {
            if (!classInfo.methods[mName]) continue;

            const captured = className + "." + mName;
            if (
                hookMethod(classInfo, mName, -1, {
                    onEnter: function (args) {
                        const record = {
                            event: "race_lifecycle",
                            class: captured,
                        };

                        // Try to read fields from self
                        const self = args[0];
                        for (const f of classInfo.fieldList) {
                            const lower = f.name.toLowerCase();
                            // Read IDs and counters
                            if (
                                (lower.includes("id") ||
                                    lower.includes("order") ||
                                    lower.includes("result") ||
                                    lower.includes("time") ||
                                    lower.includes("distance") ||
                                    lower.includes("weather") ||
                                    lower.includes("ground") ||
                                    lower.includes("grade")) &&
                                (f.type.includes("Int32") || f.type.includes("Single"))
                            ) {
                                try {
                                    if (f.type.includes("Single")) {
                                        record["field_" + f.name] = self.add(f.offset).readFloat();
                                    } else {
                                        record["field_" + f.name] = self.add(f.offset).readS32();
                                    }
                                } catch (e) {}
                            }
                            // Read string fields
                            if (f.type === "System.String" || f.type === "string") {
                                try {
                                    const strPtr = self.add(f.offset).readPointer();
                                    const str = readIl2cppString(strPtr);
                                    if (str) record["field_" + f.name] = str;
                                } catch (e) {}
                            }
                        }

                        send({ type: "collect", domain: "races", data: record });
                    },
                })
            )
                hookCount++;
        }

        // Jikkyo (commentary) triggers — these tell us what the game thinks is happening
        const jikkyoMethods = [
            "PlayComment",
            "TriggerComment",
            "OnComment",
            "AddComment",
            "ShowComment",
        ];
        for (const mName of jikkyoMethods) {
            if (!classInfo.methods[mName]) continue;

            const captured = className + "." + mName;
            if (
                hookMethod(classInfo, mName, -1, {
                    onEnter: function (args) {
                        send({
                            type: "collect",
                            domain: "races",
                            data: {
                                event: "jikkyo_comment",
                                class: captured,
                            },
                        });
                    },
                })
            )
                hookCount++;
        }
    }

    console.log("[races] " + hookCount + " hooks installed.");
    send({ type: "hook_status", module: "races", hookCount: hookCount });
})();
