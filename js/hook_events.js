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
            const capturedInfo = classInfo;
            if (
                hookMethod(classInfo, mName, -1, {
                    onEnter: function (args) {
                        const record = {
                            event: "view_begin",
                            class: captured,
                        };

                        // Read all primitive fields using the shared utility
                        const self = args[0];
                        var fields = readObjectFields(self, capturedInfo.fieldList);
                        if (fields) record.fields = fields;

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
            const capturedInfo = classInfo;
            if (
                hookMethod(classInfo, mName, -1, {
                    onEnter: function (args) {
                        var record = {
                            event: "user_choice",
                            class: captured,
                        };

                        // Read integer arguments — args[1] onwards are the
                        // actual parameters (args[0] = this in il2cpp).
                        // Choice methods commonly take an int index.
                        try {
                            var a1 = args[1];
                            if (a1) {
                                var intVal = a1.toInt32();
                                // Sanity check — choice indices are small ints
                                if (intVal >= 0 && intVal < 100) {
                                    record.arg1_int = intVal;
                                }
                            }
                        } catch (e) {}
                        try {
                            var a2 = args[2];
                            if (a2) {
                                var intVal2 = a2.toInt32();
                                if (intVal2 >= 0 && intVal2 < 100000) {
                                    record.arg2_int = intVal2;
                                }
                            }
                        } catch (e) {}

                        // Read fields from the controller (this)
                        var self = args[0];
                        var fields = readObjectFields(self, capturedInfo.fieldList);
                        if (fields) record.fields = fields;

                        send({ type: "collect", domain: "events", data: record });
                    },
                })
            )
                hookCount++;
        }
    }

    console.log("[events] " + hookCount + " hooks installed.");
    send({ type: "hook_status", module: "events", hookCount: hookCount });
})();
