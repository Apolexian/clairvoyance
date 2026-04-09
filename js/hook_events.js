// hook_events.js
// Hooks training events, story events, and choice selections.
// Loaded after il2cpp_helpers.js inside a collector IIFE.

(function () {
    "use strict";

    console.log("[events] Scanning for event classes...");

    // Keywords to match event/story/training controller classes
    const EVENT_KEYWORDS = [
        "singlemodeeventcontroller",
        "storyeventcontroller",
        "choicerewardinfo",
        "singlemodechoice",
        "singlemoderesult",
        "trainingviewcontroller",
        "singlemodetop",
    ];

    const classInfos = {};

    iterAssemblyClasses(function (classPtr, fullName, ns, name) {
        const lower = fullName.toLowerCase();
        if (
            EVENT_KEYWORDS.some(function (kw) {
                return lower.includes(kw);
            })
        ) {
            console.log("[events] Found: " + fullName);
            classInfos[fullName] = extractClassInfo(classPtr, fullName);
        }
    });

    let hookCount = 0;

    for (const [className, classInfo] of Object.entries(classInfos)) {
        // Hook BeginView / Begin / Start methods — these fire when a screen opens
        const viewMethods = ["BeginView", "Begin", "StartView", "OnStart"];
        for (const mName of viewMethods) {
            if (!classInfo.methods[mName]) continue;

            const captured = className + "." + mName;
            if (
                hookMethod(classInfo, mName, -1, {
                    onEnter: function (args) {
                        const record = {
                            event: "view_begin",
                            class: captured,
                        };

                        // Try to read any il2cpp string fields (event text, etc.)
                        const self = args[0];
                        for (const f of classInfo.fieldList) {
                            const lower = f.name.toLowerCase();
                            if (f.type === "System.String" || f.type === "string") {
                                try {
                                    const strPtr = self.add(f.offset).readPointer();
                                    const str = readIl2cppString(strPtr);
                                    if (str) record["field_" + f.name] = str;
                                } catch (e) {}
                            }
                            // Read int32 fields that look interesting
                            if (
                                (lower.includes("id") ||
                                    lower.includes("index") ||
                                    lower.includes("count")) &&
                                f.type.includes("Int32")
                            ) {
                                try {
                                    record["field_" + f.name] = self.add(f.offset).readS32();
                                } catch (e) {}
                            }
                        }

                        send({ type: "collect", domain: "events", data: record });
                    },
                })
            )
                hookCount++;
        }

        // Hook OnClick / Select / Decide methods — these fire on user choices
        const choiceMethods = [
            "OnClickDecide",
            "OnClickDecideButton",
            "OnSelect",
            "OnClickChoice",
            "SelectChoice",
            "OnDecide",
        ];
        for (const mName of choiceMethods) {
            if (!classInfo.methods[mName]) continue;

            const captured = className + "." + mName;
            if (
                hookMethod(classInfo, mName, -1, {
                    onEnter: function (args) {
                        send({
                            type: "collect",
                            domain: "events",
                            data: {
                                event: "user_choice",
                                class: captured,
                            },
                        });
                    },
                })
            )
                hookCount++;
        }
    }

    console.log("[events] " + hookCount + " hooks installed.");
    send({ type: "hook_status", module: "events", hookCount: hookCount });
})();
