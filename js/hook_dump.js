// hook_dump.js
// Data-driven field dumper. Receives class layouts from interesting.json
// (injected by Python at load time) and hooks key methods on the top-scored
// classes. When a method fires, reads all fields from `this` using known
// offsets and types, then sends the full snapshot as a collect event.
//
// This is the "actually capture game state" module.
// Loaded after il2cpp_helpers.js inside a collector IIFE.

(function () {
    "use strict";

    // Injected by Python at load time — array of {name, category, score, methods, fields}
    var DUMP_TARGETS = INJECTED_DUMP_TARGETS;

    console.log("[dump] Data-driven field dumper starting...");
    console.log("[dump] " + DUMP_TARGETS.length + " target classes to hook.");

    // Methods worth hooking — if a class has any of these, hook them.
    // These are the "something just happened" entry points.
    var HOOK_METHODS = [
        "Deserialize",
        "Serialize",
        "BeginView",
        "Begin",
        "StartView",
        "Activate",
        "LotActivate",
        "CheckTriggerAndActivate",
        "Send",
        "OnComplete",
        "OnSuccess",
        "SetResult",
        "ShowResult",
        "OnFinish",
        "BeginRace",
        "StartRace",
        "EndRace",
        "FinishRace",
        "OnClickDecide",
        "OnClickDecideButton",
        "SelectChoice",
        "Record",
        "ToRaceHorseData",
    ];

    var hookMethodSet = {};
    for (var i = 0; i < HOOK_METHODS.length; i++) {
        hookMethodSet[HOOK_METHODS[i].toLowerCase()] = true;
    }

    // ── Type readers ──────────────────────────────────────────────────
    // Given a field type string and a pointer, read the value.

    function readField(objPtr, offset, typeName) {
        try {
            if (typeName === "System.Int32" || typeName === "int") {
                return objPtr.add(offset).readS32();
            }
            if (typeName === "System.UInt32" || typeName === "uint") {
                return objPtr.add(offset).readU32();
            }
            if (typeName === "System.Int64" || typeName === "long") {
                return objPtr.add(offset).readS64().toNumber();
            }
            if (typeName === "System.UInt64" || typeName === "ulong") {
                return objPtr.add(offset).readU64().toNumber();
            }
            if (typeName === "System.Single" || typeName === "float") {
                return objPtr.add(offset).readFloat();
            }
            if (typeName === "System.Double" || typeName === "double") {
                return objPtr.add(offset).readDouble();
            }
            if (typeName === "System.Boolean" || typeName === "bool") {
                return objPtr.add(offset).readU8() !== 0;
            }
            if (typeName === "System.Byte" || typeName === "byte") {
                return objPtr.add(offset).readU8();
            }
            if (typeName === "System.SByte" || typeName === "sbyte") {
                return objPtr.add(offset).readS8();
            }
            if (typeName === "System.Int16" || typeName === "short") {
                return objPtr.add(offset).readS16();
            }
            if (typeName === "System.UInt16" || typeName === "ushort") {
                return objPtr.add(offset).readU16();
            }
            if (typeName === "System.String" || typeName === "string") {
                var strPtr = objPtr.add(offset).readPointer();
                if (strPtr.isNull()) return null;
                return readIl2cppString(strPtr);
            }
            // For arrays, just report the length (reading elements would be recursive)
            if (typeName.endsWith("[]")) {
                var arrPtr = objPtr.add(offset).readPointer();
                if (arrPtr.isNull()) return null;
                // il2cpp array: length at offset 24 (64-bit) or 12 (32-bit)
                var lenOffset = ptrSize === 8 ? 24 : 12;
                var len = arrPtr.add(lenOffset).readS32();
                return { _array: true, length: len };
            }
            // Skip complex types we can't read (other objects, generics, etc.)
            return undefined;
        } catch (e) {
            return undefined;
        }
    }

    // ── Scan and hook ─────────────────────────────────────────────────

    // First pass: find all target classes by name
    var targetLookup = Object.create(null);
    for (var ti = 0; ti < DUMP_TARGETS.length; ti++) {
        targetLookup[DUMP_TARGETS[ti].name] = DUMP_TARGETS[ti];
    }

    var foundClasses = Object.create(null);

    console.log("[dump] Scanning for target classes...");

    iterAssemblyClasses(function (classPtr, fullName, ns, name) {
        if (!(fullName in targetLookup)) return;
        foundClasses[fullName] = {
            classPtr: classPtr,
            target: targetLookup[fullName],
        };
    });

    var foundCount = Object.keys(foundClasses).length;
    console.log("[dump] Found " + foundCount + " of " + DUMP_TARGETS.length + " target classes.");

    // Second pass: extract method info and install hooks
    var hookCount = 0;

    for (var className in foundClasses) {
        (function (className) {
            var entry = foundClasses[className];
            var target = entry.target;
            var info = extractClassInfo(entry.classPtr, className);
            var category = target.category || "raw";
            var fields = target.fields || [];

            // Filter to readable fields (skip offset 0 which are usually static/constants)
            var readableFields = [];
            for (var fi = 0; fi < fields.length; fi++) {
                var f = fields[fi];
                if (f.offset > 0 && f.type) {
                    readableFields.push(f);
                }
            }

            // Find hookable methods on this class
            var methodNames = Object.keys(info.methods);
            for (var mi = 0; mi < methodNames.length; mi++) {
                (function (methodName) {
                    if (!(methodName.toLowerCase() in hookMethodSet)) return;

                    if (
                        hookMethod(info, methodName, -1, {
                            onEnter: function (args) {
                                var self = args[0];
                                if (!self || self.isNull()) return;

                                // Read all fields from this
                                var snapshot = Object.create(null);
                                for (var ri = 0; ri < readableFields.length; ri++) {
                                    var rf = readableFields[ri];
                                    var val = readField(self, rf.offset, rf.type);
                                    if (val !== undefined) {
                                        snapshot[rf.name] = val;
                                    }
                                }

                                send({
                                    type: "collect",
                                    domain: category,
                                    data: {
                                        event: "dump",
                                        class: className,
                                        method: methodName,
                                        fields: snapshot,
                                    },
                                });
                            },
                        })
                    ) {
                        hookCount++;
                    }
                })(methodNames[mi]);
            }
        })(className);
    }

    console.log("[dump] " + hookCount + " dump hooks installed across " + foundCount + " classes.");
    send({ type: "hook_status", module: "dump", hookCount: hookCount });
})();
